#!/usr/bin/env python3
"""
MCP Server with Codex-style filesystem tools plus localhost QA evidence tools.

Adds dedicated tools for ChatGPT QA review workflows:
- start_localhost: start a local dev server as a background process
- localhost_status: check registered process and optional localhost URL health
- stop_localhost: stop a registered localhost process
- capture_web_screenshot: open a localhost URL with Playwright and save a screenshot
- capture_web_screenshot_batch: capture multiple localhost screenshots in one call

Security model:
- All filesystem paths are restricted to the allowed workspace root.
- Browser targets are restricted to localhost / 127.0.0.1 / ::1 URLs only.
- Screenshot and log paths are always resolved inside the same repo/workspace.
- Long-running app servers are tracked in .mcp/runtime/localhost_processes.json.
"""

import os
import sys
import json
import time
import shlex
import signal
import socket
import platform
import subprocess
import argparse
import hmac
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from http.server import HTTPServer, BaseHTTPRequestHandler

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "Local QA Filesystem Server"
SERVER_VERSION = "1.4.0"

# Reasonable execution limits for synchronous shell commands.
DEFAULT_TIMEOUT_SEC = 30
MAX_STDOUT_CHARS = 200_000
MAX_STDERR_CHARS = 200_000

# QA evidence defaults. These are relative to the allowed repo/workspace root.
RUNTIME_DIR = ".mcp/runtime"
PROCESS_REGISTRY_PATH = f"{RUNTIME_DIR}/localhost_processes.json"
DEFAULT_LOG_DIR = "docs/qa/evidence/logs"
DEFAULT_SCREENSHOT_DIR = "docs/qa/evidence/screenshots"
DEFAULT_SCREENSHOT_WAIT_MS = 1000
DEFAULT_BROWSER_TIMEOUT_MS = 30_000
DEFAULT_VIEWPORT = {"width": 1440, "height": 1000}
LOCALHOST_NAMES = {"localhost", "127.0.0.1", "::1"}


class MCPSSEHandler(BaseHTTPRequestHandler):
    def __init__(self, allowed_directory: Path, auth_token: str | None = None, *args, **kwargs):
        self.allowed_directory = allowed_directory.resolve()
        self.auth_token = (auth_token or "").strip()
        super().__init__(*args, **kwargs)

    # -------- utilities --------
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-MCP-Token")

    def _send_json(self, status: int, payload: dict):
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def _server_info(self) -> dict:
        return {"name": SERVER_NAME, "version": SERVER_VERSION}

    def _request_path(self) -> str:
        return urlparse(self.path).path

    def _provided_token(self) -> str:
        auth_header = self.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()
        header_token = self.headers.get("X-MCP-Token", "")
        if header_token:
            return header_token.strip()
        parsed = urlparse(self.path)
        values = parse_qs(parsed.query).get("token") or []
        return values[0].strip() if values else ""

    def _is_authorized(self) -> bool:
        if not self.auth_token:
            return True
        candidate = self._provided_token()
        return bool(candidate) and hmac.compare_digest(candidate, self.auth_token)

    def _send_unauthorized(self):
        self._send_json(401, {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32001, "message": "Unauthorized: missing or invalid MCP token"},
        })

    # -------- HTTP verbs --------
    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if not self._is_authorized():
            self._send_unauthorized()
            return
        request_path = self._request_path()
        if request_path == "/sse/":
            self.handle_sse_connection()
        elif request_path == "/":
            self._send_json(200, {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": self._server_info(),
                },
            })
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if not self._is_authorized():
            self._send_unauthorized()
            return
        request_path = self._request_path()
        if request_path in ("/", "/sse/"):
            self.handle_mcp_message()
        else:
            self.send_error(404, "Not Found")

    # -------- SSE --------
    def handle_sse_connection(self):
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        # Non-initialization notification
        self.send_sse_event("message", {
            "jsonrpc": "2.0",
            "method": "notifications/server/ready",
            "params": {"message": "SSE stream established"},
        })
        try:
            while True:
                time.sleep(30)
                self.send_sse_event("ping", {"type": "ping"})
        except Exception:
            pass

    def send_sse_event(self, event_type: str, data: dict):
        try:
            self.wfile.write(f"event: {event_type}\n".encode("utf-8"))
            self.wfile.write(f"data: {json.dumps(data)}\n\n".encode("utf-8"))
            self.wfile.flush()
        except Exception:
            pass

    # -------- JSON-RPC --------
    def handle_mcp_message(self):
        message = None
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                self._send_json(400, {
                    "jsonrpc": "2.0", "id": None,
                    "error": {"code": -32600, "message": "No content"},
                })
                return
            raw = self.rfile.read(content_length).decode("utf-8")
            message = json.loads(raw)
            response = self.process_mcp_message(message)
            self._send_json(200, response)
        except Exception as e:
            msg_id = None
            try:
                msg_id = message.get("id")  # best effort
            except Exception:
                pass
            self._send_json(500, {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32603, "message": str(e)},
            })

    def process_mcp_message(self, message: dict) -> dict:
        method = message.get("method")
        params = message.get("params", {}) or {}
        msg_id = message.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": self._server_info(),
                },
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": self._tool_definitions()},
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {}) or {}
            try:
                if tool_name == "shell":
                    result = self.handle_shell(tool_args)
                elif tool_name == "apply_patch":
                    result = self.handle_apply_patch(tool_args.get("patch", ""))
                elif tool_name == "search":
                    result = self.handle_search(tool_args.get("query", ""))
                elif tool_name == "fetch":
                    result = self.handle_fetch(tool_args.get("id", ""))
                elif tool_name == "write_file":
                    result = self.handle_write_file(tool_args.get("path", ""), tool_args.get("content", ""))
                elif tool_name == "create_directory":
                    result = self.handle_create_directory(tool_args.get("path", ""))
                elif tool_name == "delete_file":
                    result = self.handle_delete_file(tool_args)
                elif tool_name == "start_localhost":
                    result = self.handle_start_localhost(tool_args)
                elif tool_name == "localhost_status":
                    result = self.handle_localhost_status(tool_args)
                elif tool_name == "stop_localhost":
                    result = self.handle_stop_localhost(tool_args)
                elif tool_name == "capture_web_screenshot":
                    result = self.handle_capture_web_screenshot(tool_args)
                elif tool_name == "capture_web_screenshot_batch":
                    result = self.handle_capture_web_screenshot_batch(tool_args)
                else:
                    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2), "mimeType": "application/json"}
                        ]
                    }
                }
            except Exception as e:
                return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32000, "message": str(e)}}

        else:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}

    def _tool_definitions(self) -> list:
        return [
            # --- Codex-style tools ---
            {
                "name": "shell",
                "description": "Execute short shell commands within the allowed workspace. Use start_localhost for long-running dev servers.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "oneOf": [
                                {"type": "string", "description": "Command string, shlex-split before execution"},
                                {"type": "array", "items": {"type": "string"}, "description": "Command argv"},
                            ]
                        },
                        "workdir": {"type": "string", "description": "Working directory, relative or absolute within allowed root"},
                        "timeout": {"type": "integer", "description": "Timeout in seconds"},
                    },
                    "required": ["command", "workdir"],
                },
            },
            {
                "name": "apply_patch",
                "description": "Apply a multi-file Codex-style patch. Supports Add/Update/Delete File, unified hunks, and full-file replacement blocks.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "patch": {"type": "string", "description": "Patch text"},
                    },
                    "required": ["patch"],
                },
            },

            # --- Filesystem tools ---
            {
                "name": "search",
                "description": "Search for files and directories",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search query, empty means list root"}},
                    "required": ["query"],
                },
            },
            {
                "name": "fetch",
                "description": "Fetch file or directory contents",
                "inputSchema": {
                    "type": "object",
                    "properties": {"id": {"type": "string", "description": "File or directory path"}},
                    "required": ["id"],
                },
            },
            {
                "name": "write_file",
                "description": "Write a UTF-8 text file inside the allowed workspace, creating parents",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["path", "content"],
                },
            },
            {
                "name": "create_directory",
                "description": "Create a directory inside the allowed workspace, including parents",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
            {
                "name": "delete_file",
                "description": "Delete one or more files/directories inside the allowed workspace. Accepts path, id, file_id, target, or paths[]. Verifies deletion.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to delete, relative to workspace root"},
                        "id": {"type": "string", "description": "Alias for path, useful when deleting a fetched/search result"},
                        "file_id": {"type": "string", "description": "Alias for path"},
                        "target": {"type": "string", "description": "Alias for path"},
                        "paths": {"type": "array", "items": {"type": "string"}, "description": "Multiple paths to delete"},
                        "recursive": {"type": "boolean", "description": "Allow recursive directory deletion, default true"},
                        "missing_ok": {"type": "boolean", "description": "Treat missing paths as success, default false"}
                    },
                    "required": [],
                },
            },

            # --- Localhost QA tools ---
            {
                "name": "start_localhost",
                "description": "Start a local development server as a background process and register its PID for QA review",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Stable process name, default: default"},
                        "command": {
                            "oneOf": [
                                {"type": "string", "description": "Command string, shlex-split before execution"},
                                {"type": "array", "items": {"type": "string"}, "description": "Command argv"},
                            ]
                        },
                        "workdir": {"type": "string", "description": "Working directory, relative or absolute within allowed root"},
                        "url": {"type": "string", "description": "Optional localhost URL for readiness checks"},
                        "port": {"type": "integer", "description": "Optional port. If url is omitted, http://localhost:<port> is used for readiness checks"},
                        "log_path": {"type": "string", "description": "Optional log path inside repo"},
                        "wait_until_ready": {"type": "boolean", "description": "Wait for URL/port health before returning, default: true when URL or port is provided"},
                        "ready_timeout": {"type": "integer", "description": "Readiness timeout in seconds, default: 30"},
                        "force_restart": {"type": "boolean", "description": "Stop existing process with same name before starting"},
                    },
                    "required": ["command", "workdir"],
                },
            },
            {
                "name": "localhost_status",
                "description": "Check registered localhost process status and optional localhost URL health",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Registered process name, default: default"},
                        "url": {"type": "string", "description": "Optional localhost URL to check"},
                        "timeout": {"type": "integer", "description": "URL check timeout in seconds, default: 5"},
                    },
                },
            },
            {
                "name": "stop_localhost",
                "description": "Stop a registered localhost background process by name or PID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Registered process name, default: default"},
                        "pid": {"type": "integer", "description": "Optional process PID to stop"},
                        "timeout": {"type": "integer", "description": "Graceful stop timeout in seconds, default: 10"},
                    },
                },
            },
            {
                "name": "capture_web_screenshot",
                "description": "Open a localhost URL with Playwright and save a QA evidence screenshot inside the repo",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Localhost URL only"},
                        "output_path": {"type": "string", "description": "Optional screenshot path inside repo. Auto-generated if omitted"},
                        "full_page": {"type": "boolean", "description": "Capture full scrollable page, default: true"},
                        "wait_ms": {"type": "integer", "description": "Delay after navigation before screenshot, default: 1000"},
                        "timeout_ms": {"type": "integer", "description": "Navigation timeout in ms, default: 30000"},
                        "wait_until": {"type": "string", "description": "Playwright navigation wait condition: domcontentloaded, load, or networkidle. Default: domcontentloaded"},
                        "browser": {"type": "string", "description": "chromium, firefox, or webkit. Default: chromium"},
                        "viewport": {
                            "type": "object",
                            "properties": {
                                "width": {"type": "integer"},
                                "height": {"type": "integer"},
                            },
                            "description": "Viewport size, default 1440x1000",
                        },
                        "block_external_requests": {"type": "boolean", "description": "Abort non-localhost subresource requests, default: false"},
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "capture_web_screenshot_batch",
                "description": "Capture multiple localhost screenshots in one QA evidence batch",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "screenshots": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string"},
                                    "output_path": {"type": "string"},
                                    "wait_ms": {"type": "integer"},
                                    "full_page": {"type": "boolean"},
                                },
                                "required": ["url"],
                            },
                        },
                        "full_page": {"type": "boolean", "description": "Default for items, default: true"},
                        "wait_ms": {"type": "integer", "description": "Default for items, default: 1000"},
                        "timeout_ms": {"type": "integer", "description": "Navigation timeout in ms, default: 30000"},
                        "wait_until": {"type": "string", "description": "Playwright navigation wait condition: domcontentloaded, load, or networkidle. Default: domcontentloaded"},
                        "browser": {"type": "string", "description": "chromium, firefox, or webkit. Default: chromium"},
                        "viewport": {
                            "type": "object",
                            "properties": {
                                "width": {"type": "integer"},
                                "height": {"type": "integer"},
                            },
                        },
                        "block_external_requests": {"type": "boolean", "description": "Abort non-localhost subresource requests, default: false"},
                    },
                    "required": ["screenshots"],
                },
            },
        ]

    # -------- Codex-style tool impls --------
    def handle_shell(self, args: dict) -> dict:
        """
        Execute a short shell command similar to Codex CLI's shell tool.
        Long-running dev servers should use start_localhost instead.
        """
        if "command" not in args or "workdir" not in args:
            raise ValueError("shell requires 'command' and 'workdir'")

        workdir = self.validate_path(args.get("workdir", ""))
        if not workdir.exists() or not workdir.is_dir():
            raise ValueError(f"Invalid workdir: {workdir}")

        argv = self._parse_command(args["command"])
        timeout = int(args.get("timeout", DEFAULT_TIMEOUT_SEC))
        try:
            proc = subprocess.run(
                argv,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._restricted_env(),
            )
        except subprocess.TimeoutExpired as te:
            return {
                "ok": False,
                "exitCode": None,
                "timedOut": True,
                "stdout": (te.stdout or "")[:MAX_STDOUT_CHARS],
                "stderr": (te.stderr or f"Timed out after {timeout}s")[:MAX_STDERR_CHARS],
            }

        return {
            "ok": proc.returncode == 0,
            "exitCode": proc.returncode,
            "timedOut": False,
            "stdout": (proc.stdout or "")[:MAX_STDOUT_CHARS],
            "stderr": (proc.stderr or "")[:MAX_STDERR_CHARS],
        }

    def handle_apply_patch(self, patch_text: str) -> dict:
        """
        Apply Codex-style patches safely.

        Supported:
          *** Begin Patch
          *** Add File: path
          +new content
          *** Update File: path
          @@
          -old
          +new
          *** Delete File: path
          *** End Patch

        Also supports the legacy full-file replacement shape where an Update File
        body has no unified-diff markers. Unsupported patch shapes fail loudly
        instead of writing malformed patch text into the target file.
        """
        if not patch_text or "*** Begin Patch" not in patch_text or "*** End Patch" not in patch_text:
            raise ValueError("Patch must contain '*** Begin Patch' and '*** End Patch'")

        lines = patch_text.splitlines(keepends=True)
        try:
            begin_idx = next(i for i, line in enumerate(lines) if line.strip() == "*** Begin Patch")
            end_idx = max(i for i, line in enumerate(lines) if line.strip() == "*** End Patch")
        except StopIteration as exc:
            raise ValueError("Malformed patch block") from exc

        idx = begin_idx + 1
        updated: list[str] = []
        added: list[str] = []
        deleted: list[str] = []

        while idx < end_idx:
            line = lines[idx]
            stripped = line.strip()
            if not stripped:
                idx += 1
                continue

            action = None
            rel_path = None
            for prefix, action_name in (
                ("*** Add File:", "add"),
                ("*** Update File:", "update"),
                ("*** Delete File:", "delete"),
            ):
                if stripped.startswith(prefix):
                    action = action_name
                    rel_path = stripped[len(prefix):].strip()
                    break

            if not action or not rel_path:
                raise ValueError(f"Unsupported patch line: {stripped}")

            idx += 1
            body_lines = []
            while idx < end_idx and not lines[idx].strip().startswith(("*** Add File:", "*** Update File:", "*** Delete File:")):
                body_lines.append(lines[idx])
                idx += 1

            target = self.validate_path(rel_path)
            rel = str(target.relative_to(self.allowed_directory))

            if action == "add":
                if target.exists():
                    raise FileExistsError(f"Add File target already exists: {rel}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(self._normalize_added_file_body(body_lines), encoding="utf-8")
                added.append(rel)
            elif action == "delete":
                if body_lines and any(line.strip() for line in body_lines):
                    raise ValueError(f"Delete File block for {rel} must not contain body text")
                if not target.exists():
                    raise FileNotFoundError(f"Delete File target does not exist: {rel}")
                if target.is_dir():
                    import shutil
                    shutil.rmtree(target)
                else:
                    target.unlink()
                if target.exists():
                    raise RuntimeError(f"Delete File failed; target still exists: {rel}")
                deleted.append(rel)
            elif action == "update":
                if not target.exists():
                    raise FileNotFoundError(f"Update File target does not exist: {rel}")
                if self._looks_like_unified_patch_body(body_lines):
                    self._apply_unified_patch_to_file(target, body_lines)
                else:
                    target.write_text("".join(body_lines), encoding="utf-8")
                updated.append(rel)

        return {"success": True, "updated": updated, "added": added, "deleted": deleted}

    def _normalize_added_file_body(self, body_lines: list[str]) -> str:
        meaningful = [line for line in body_lines if line.strip()]
        if meaningful and all(line.startswith("+") for line in meaningful):
            return "".join(line[1:] if line.startswith("+") else line for line in body_lines)
        return "".join(body_lines)

    def _looks_like_unified_patch_body(self, body_lines: list[str]) -> bool:
        if any(line.startswith("@@") for line in body_lines):
            return True
        has_minus = any(line.startswith("-") and not line.startswith("---") for line in body_lines)
        has_plus = any(line.startswith("+") and not line.startswith("+++") for line in body_lines)
        return has_minus and has_plus

    def _apply_unified_patch_to_file(self, target: Path, body_lines: list[str]) -> None:
        original = target.read_text(encoding="utf-8").splitlines(keepends=True)
        result = list(original)
        cursor = 0
        idx = 0
        applied_hunks = 0

        implicit_hunk = not any(line.startswith("@@") for line in body_lines)
        if implicit_hunk:
            body_lines = ["@@\n"] + body_lines

        while idx < len(body_lines):
            line = body_lines[idx]
            if not line.strip():
                idx += 1
                continue
            if not line.startswith("@@"):
                raise ValueError(f"Expected unified hunk header starting with @@, got: {line.strip()}")
            header = line
            header_start = self._parse_hunk_start_line(header)
            idx += 1

            hunk_lines = []
            while idx < len(body_lines) and not body_lines[idx].startswith("@@"):
                hunk_lines.append(body_lines[idx])
                idx += 1

            old_segment = []
            new_segment = []
            for hline in hunk_lines:
                if hline.startswith("\\"):
                    continue
                if not hline:
                    continue
                marker = hline[0]
                content = hline[1:]
                if marker == " ":
                    old_segment.append(content)
                    new_segment.append(content)
                elif marker == "-":
                    old_segment.append(content)
                elif marker == "+":
                    new_segment.append(content)
                elif hline.strip() == "":
                    # Rare tolerance for bare blank lines inside generated patches.
                    old_segment.append(hline)
                    new_segment.append(hline)
                else:
                    raise ValueError(f"Unsupported hunk line: {hline.strip()}")

            loc = self._find_subsequence(result, old_segment, start=cursor)
            if loc < 0 and header_start is not None:
                approx = max(0, header_start - 1)
                loc = self._find_subsequence(result, old_segment, start=approx)
            if loc < 0:
                loc = self._find_subsequence(result, old_segment, start=0)
            if loc < 0:
                raise ValueError("Patch hunk did not match target file; no changes were applied")

            result[loc: loc + len(old_segment)] = new_segment
            cursor = loc + len(new_segment)
            applied_hunks += 1

        if applied_hunks == 0:
            raise ValueError("No patch hunks were applied")
        target.write_text("".join(result), encoding="utf-8")

    def _parse_hunk_start_line(self, header: str) -> int | None:
        # Supports headers like: @@ -12,4 +12,5 @@
        try:
            import re
            match = re.search(r"@@\s+-(\d+)", header)
            return int(match.group(1)) if match else None
        except Exception:
            return None

    def _find_subsequence(self, haystack: list[str], needle: list[str], start: int = 0) -> int:
        if not needle:
            return max(0, min(start, len(haystack)))
        max_start = len(haystack) - len(needle)
        for pos in range(max(0, start), max_start + 1):
            if haystack[pos: pos + len(needle)] == needle:
                return pos
        return -1

    def _restricted_env(self):
        """Environment stripped down; PATH preserved for common tools."""
        env = os.environ.copy()
        # You can further lock this down, for example remove cloud credentials.
        for k in list(env.keys()):
            if k.upper().startswith(("AWS_", "GCP_", "AZURE_", "KUBECONFIG", "SSH_")):
                env.pop(k, None)
        return env

    # -------- Localhost QA tool impls --------
    def handle_start_localhost(self, args: dict) -> dict:
        if "command" not in args or "workdir" not in args:
            raise ValueError("start_localhost requires 'command' and 'workdir'")

        name = self._safe_process_name(args.get("name") or "default")
        workdir = self.validate_path(args.get("workdir", ""))
        if not workdir.exists() or not workdir.is_dir():
            raise ValueError(f"Invalid workdir: {workdir}")

        registry = self._load_process_registry()
        existing = registry.get("processes", {}).get(name)
        if existing and self._is_pid_running(int(existing.get("pid", -1))):
            if args.get("force_restart"):
                self._stop_process_record(existing, timeout=int(args.get("timeout", 10)))
                registry = self._load_process_registry()
            else:
                return {
                    "ok": True,
                    "alreadyRunning": True,
                    "name": name,
                    "pid": existing.get("pid"),
                    "url": existing.get("url"),
                    "log_path": existing.get("log_path"),
                    "message": "Process already running. Use force_restart=true to restart it.",
                }

        argv = self._parse_command(args["command"])
        port = args.get("port")
        url = args.get("url") or (f"http://localhost:{int(port)}" if port else None)
        if url:
            self._validate_localhost_url(url)

        log_path_arg = args.get("log_path") or self._default_log_path(name)
        log_path = self.validate_path(log_path_arg)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        creationflags = 0
        popen_kwargs = {}
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            popen_kwargs["start_new_session"] = True

        log_file = open(log_path, "ab")
        try:
            proc = subprocess.Popen(
                argv,
                cwd=str(workdir),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                env=self._restricted_env(),
                creationflags=creationflags,
                **popen_kwargs,
            )
        finally:
            # Child process keeps the OS file handle; close parent's handle.
            log_file.close()

        record = {
            "name": name,
            "pid": proc.pid,
            "command": argv,
            "workdir": str(workdir.relative_to(self.allowed_directory)),
            "url": url,
            "port": int(port) if port else None,
            "log_path": str(log_path.relative_to(self.allowed_directory)),
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "platform": platform.system(),
        }
        registry.setdefault("processes", {})[name] = record
        self._save_process_registry(registry)

        wait_until_ready = args.get("wait_until_ready")
        if wait_until_ready is None:
            wait_until_ready = bool(url)
        ready_timeout = int(args.get("ready_timeout", 30))
        ready = None
        if wait_until_ready and url:
            ready = self._wait_for_localhost_url(url, timeout_sec=ready_timeout)

        return {
            "ok": True,
            "alreadyRunning": False,
            "name": name,
            "pid": proc.pid,
            "url": url,
            "port": int(port) if port else None,
            "log_path": record["log_path"],
            "registry_path": PROCESS_REGISTRY_PATH,
            "ready": ready,
        }

    def handle_localhost_status(self, args: dict) -> dict:
        name = self._safe_process_name(args.get("name") or "default")
        registry = self._load_process_registry()
        record = registry.get("processes", {}).get(name)
        pid = int(record.get("pid")) if record and record.get("pid") else None
        running = self._is_pid_running(pid) if pid else False

        url = args.get("url") or (record.get("url") if record else None)
        health = None
        if url:
            self._validate_localhost_url(url)
            health = self._check_localhost_url(url, timeout_sec=int(args.get("timeout", 5)))

        return {
            "ok": True,
            "name": name,
            "registered": record is not None,
            "running": running,
            "pid": pid,
            "url": url,
            "health": health,
            "record": record,
        }

    def handle_stop_localhost(self, args: dict) -> dict:
        registry = self._load_process_registry()
        timeout = int(args.get("timeout", 10))
        name = self._safe_process_name(args.get("name") or "default")
        pid_arg = args.get("pid")

        record = None
        if pid_arg:
            pid = int(pid_arg)
            for process_name, candidate in registry.get("processes", {}).items():
                if int(candidate.get("pid", -1)) == pid:
                    name = process_name
                    record = candidate
                    break
            if not record:
                record = {"name": name, "pid": pid}
        else:
            record = registry.get("processes", {}).get(name)
            if not record:
                return {"ok": True, "stopped": False, "name": name, "message": "No registered process found"}

        stopped = self._stop_process_record(record, timeout=timeout)

        # Remove from registry when stopped or no longer running.
        try:
            pid = int(record.get("pid"))
            if stopped or not self._is_pid_running(pid):
                registry.get("processes", {}).pop(name, None)
                self._save_process_registry(registry)
        except Exception:
            pass

        return {
            "ok": True,
            "stopped": stopped,
            "name": name,
            "pid": record.get("pid"),
            "running_after_stop": self._is_pid_running(int(record.get("pid", -1))),
        }

    def handle_capture_web_screenshot(self, args: dict) -> dict:
        item = dict(args)
        return self._capture_one_screenshot(
            url=item.get("url"),
            output_path=item.get("output_path"),
            full_page=item.get("full_page", True),
            wait_ms=int(item.get("wait_ms", DEFAULT_SCREENSHOT_WAIT_MS)),
            timeout_ms=int(item.get("timeout_ms", DEFAULT_BROWSER_TIMEOUT_MS)),
            wait_until=item.get("wait_until", "domcontentloaded"),
            browser_name=item.get("browser", "chromium"),
            viewport=item.get("viewport") or DEFAULT_VIEWPORT,
            block_external_requests=bool(item.get("block_external_requests", False)),
        )

    def handle_capture_web_screenshot_batch(self, args: dict) -> dict:
        screenshots = args.get("screenshots") or []
        if not isinstance(screenshots, list) or not screenshots:
            raise ValueError("capture_web_screenshot_batch requires a non-empty screenshots array")

        results = []
        errors = []
        for idx, item in enumerate(screenshots, start=1):
            try:
                if not isinstance(item, dict):
                    raise ValueError(f"Screenshot item {idx} must be an object")
                merged = dict(args)
                merged.update(item)
                # Remove the batch list so it does not pollute the single-shot args.
                merged.pop("screenshots", None)
                result = self.handle_capture_web_screenshot(merged)
                result["index"] = idx
                results.append(result)
            except Exception as e:
                errors.append({"index": idx, "url": item.get("url") if isinstance(item, dict) else None, "error": str(e)})

        return {
            "ok": len(errors) == 0,
            "captured": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        }

    def _capture_one_screenshot(self, url: str, output_path: str, full_page: bool, wait_ms: int,
                                timeout_ms: int, wait_until: str, browser_name: str, viewport: dict,
                                block_external_requests: bool) -> dict:
        if not url:
            raise ValueError("url is required")
        self._validate_localhost_url(url)

        if not output_path:
            output_path = self._default_screenshot_path(url)
        screenshot_path = self.validate_path(output_path)
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)

        wait_until = (wait_until or "domcontentloaded").lower().strip()
        if wait_until not in {"domcontentloaded", "load", "networkidle"}:
            raise ValueError("wait_until must be one of: domcontentloaded, load, networkidle")

        browser_name = (browser_name or "chromium").lower().strip()
        if browser_name not in {"chromium", "firefox", "webkit"}:
            raise ValueError("browser must be one of: chromium, firefox, webkit")

        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed in the Python environment running this MCP server. "
                "Install it with: python -m pip install playwright && python -m playwright install chromium"
            ) from exc

        viewport = self._normalize_viewport(viewport)
        final_url = None
        title = None
        status = None
        try:
            with sync_playwright() as p:
                browser_type = getattr(p, browser_name)
                browser = browser_type.launch(headless=True)
                context = browser.new_context(viewport=viewport)

                if block_external_requests:
                    def route_handler(route):
                        request_url = route.request.url
                        parsed = urlparse(request_url)
                        if self._is_localhost_hostname(parsed.hostname):
                            route.continue_()
                        else:
                            route.abort()
                    context.route("**/*", route_handler)

                page = context.new_page()
                response = page.goto(url, wait_until=wait_until, timeout=timeout_ms)
                final_url = page.url
                self._validate_localhost_url(final_url)
                if response:
                    status = response.status
                if wait_ms > 0:
                    page.wait_for_timeout(wait_ms)
                title = page.title()
                page.screenshot(path=str(screenshot_path), full_page=bool(full_page))
                browser.close()
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"Timed out while loading localhost page: {url}") from exc
        except Exception as exc:
            message = str(exc)
            if "Executable doesn't exist" in message or "playwright install" in message.lower():
                raise RuntimeError(
                    "Playwright browser binaries are missing in the Python environment running this MCP server. "
                    "Run: python -m playwright install chromium"
                ) from exc
            raise

        return {
            "ok": True,
            "url": url,
            "final_url": final_url,
            "status": status,
            "title": title,
            "output_path": str(screenshot_path.relative_to(self.allowed_directory)),
            "full_page": bool(full_page),
            "wait_ms": wait_ms,
            "browser": browser_name,
            "wait_until": wait_until,
            "viewport": viewport,
            "bytes": screenshot_path.stat().st_size if screenshot_path.exists() else None,
        }

    # -------- Filesystem tools --------
    def handle_search(self, query: str) -> dict:
        results = []
        q = (query or "").lower().strip()
        if not q:
            target = self.allowed_directory
            if target.exists() and target.is_dir():
                for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                    rel = item.relative_to(self.allowed_directory)
                    results.append({"id": str(rel), "title": f"{'[DIR] ' if item.is_dir() else ''}{item.name}", "url": f"file://{item.resolve()}"})
        else:
            for path in self.allowed_directory.rglob("*"):
                try:
                    rel = path.relative_to(self.allowed_directory)
                    if q in path.name.lower() or q in str(rel).lower():
                        results.append({"id": str(rel), "title": f"{'[DIR] ' if path.is_dir() else ''}{path.name}", "url": f"file://{path.resolve()}"})
                except Exception:
                    continue
        return {"results": results[:50]}

    def handle_fetch(self, file_id: str) -> dict:
        if not file_id:
            raise ValueError("File ID is required")
        path = self.validate_path(file_id)
        if not path.exists():
            raise ValueError(f"Not found: {file_id}")
        if path.is_dir():
            items = []
            for item in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                items.append(f"{'[DIR] ' if item.is_dir() else ''}{item.name}")
            content = f"Directory: {file_id}\n\nContents:\n" + "\n".join(items)
            return {"id": file_id, "title": path.name, "text": content, "url": f"file://{path.resolve()}", "metadata": {"type": "directory"}}
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("File too large (limit 1MB)")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = f"[Binary file: {path.suffix or 'unknown'}]"
        return {"id": file_id, "title": path.name, "text": text, "url": f"file://{path.resolve()}", "metadata": {"type": "file", "size": path.stat().st_size}}

    def handle_write_file(self, dest: str, content: str) -> dict:
        if not dest:
            raise ValueError("File path is required")
        path = self.validate_path(dest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"success": True, "message": f"Wrote {len(content)} bytes to {dest}", "path": dest}

    def handle_create_directory(self, p: str) -> dict:
        if not p:
            raise ValueError("Directory path is required")
        path = self.validate_path(p)
        path.mkdir(parents=True, exist_ok=True)
        return {"success": True, "message": f"Created directory: {p}", "path": p}

    def handle_delete_file(self, args) -> dict:
        """
        Delete one or more paths inside the allowed workspace.

        v1.4 hardening notes:
        - Accepts path/id/file_id/target aliases and paths[] arrays.
        - Accepts file:// URLs that resolve inside the workspace.
        - Treats a leading slash like /docs/foo as workspace-relative when it is
          not a real absolute path inside the workspace. This matches how some
          MCP clients display repo-root paths.
        - Verifies that each path no longer exists after deletion.
        """
        if isinstance(args, str):
            args = {"path": args}
        if args is None:
            args = {}
        if not isinstance(args, dict):
            raise ValueError("delete_file arguments must be an object or path string")

        recursive = bool(args.get("recursive", True))
        missing_ok = bool(args.get("missing_ok", False))

        requested = []
        if isinstance(args.get("paths"), list):
            requested.extend([x for x in args.get("paths", []) if isinstance(x, str) and x.strip()])
        for key in ("path", "id", "file_id", "target"):
            val = args.get(key)
            if isinstance(val, str) and val.strip():
                requested.append(val)
                break

        # De-duplicate while preserving order.
        seen = set()
        paths = []
        for item in requested:
            item = item.strip()
            if item not in seen:
                paths.append(item)
                seen.add(item)

        if not paths:
            raise ValueError("Path is required. Provide path, id, file_id, target, or paths[].")

        deleted = []
        errors = []
        for raw in paths:
            try:
                path = self._normalize_delete_target(raw)
                rel = str(path.relative_to(self.allowed_directory))

                if not path.exists() and not path.is_symlink():
                    if missing_ok:
                        deleted.append({
                            "path": rel,
                            "requested": raw,
                            "deleted": False,
                            "missing": True,
                            "exists_after": False,
                            "type": "missing",
                        })
                        continue
                    raise FileNotFoundError(f"Path does not exist: {rel}")

                item_type = "symlink" if path.is_symlink() else ("directory" if path.is_dir() else "file")

                if path.is_dir() and not path.is_symlink():
                    if not recursive:
                        raise IsADirectoryError(f"Path is a directory and recursive=false: {rel}")
                    import shutil
                    shutil.rmtree(path)
                else:
                    try:
                        path.unlink()
                    except PermissionError:
                        try:
                            os.chmod(path, 0o700)
                        except Exception:
                            pass
                        path.unlink()

                # Some mounted filesystems need a tiny delay before the directory
                # entry disappears from stat results.
                exists_after = True
                for _ in range(10):
                    exists_after = path.exists() or path.is_symlink()
                    if not exists_after:
                        break
                    time.sleep(0.05)

                if exists_after:
                    raise RuntimeError(f"Delete failed; path still exists after unlink/rmtree: {rel}")

                deleted.append({
                    "path": rel,
                    "requested": raw,
                    "deleted": True,
                    "missing": False,
                    "exists_after": False,
                    "type": item_type,
                })
            except Exception as exc:
                errors.append({"requested": raw, "error": str(exc)})

        success = len(errors) == 0
        return {
            "success": success,
            "deleted_count": len([x for x in deleted if x.get("deleted")]),
            "requested_count": len(paths),
            "deleted": deleted,
            "errors": errors,
            "message": "Deleted requested path(s)" if success else "One or more delete operations failed",
        }

    def _normalize_delete_target(self, raw: str) -> Path:
        target = (raw or "").strip()
        if not target:
            raise ValueError("Delete target is empty")

        # Accept file:// URLs from search/fetch results, but only if they resolve
        # inside the allowed workspace.
        if target.startswith("file://"):
            parsed = urlparse(target)
            target = parsed.path

        # Some clients display repo-root paths with a leading slash, e.g.
        # /docs/qa/file.txt. If that absolute path is not already inside the
        # allowed workspace, treat it as workspace-relative docs/qa/file.txt.
        if target.startswith("/"):
            absolute_candidate = Path(target).resolve()
            allowed = str(self.allowed_directory)
            if str(absolute_candidate).startswith(allowed):
                return self.validate_path(str(absolute_candidate))
            target = target.lstrip("/")

        return self.validate_path(target)

    # -------- process registry helpers --------
    def _load_process_registry(self) -> dict:
        path = self.validate_path(PROCESS_REGISTRY_PATH)
        if not path.exists():
            return {"processes": {}}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"processes": {}}
            data.setdefault("processes", {})
            return data
        except Exception:
            return {"processes": {}}

    def _save_process_registry(self, registry: dict) -> None:
        path = self.validate_path(PROCESS_REGISTRY_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

    def _is_pid_running(self, pid: int) -> bool:
        if not pid or pid <= 0:
            return False
        if os.name == "nt":
            try:
                proc = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return str(pid) in (proc.stdout or "")
            except Exception:
                return False

        # POSIX: os.kill(pid, 0) returns True for zombies, so check /proc first
        # when available. A zombie has already stopped and should not be treated
        # as a running localhost server.
        proc_stat = Path(f"/proc/{pid}/stat")
        if proc_stat.exists():
            try:
                stat_text = proc_stat.read_text(encoding="utf-8", errors="ignore")
                state = stat_text.split()[2] if len(stat_text.split()) > 2 else ""
                if state == "Z":
                    self._reap_child_if_possible(pid)
                    return False
            except Exception:
                pass

        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except Exception:
            return False

    def _reap_child_if_possible(self, pid: int) -> None:
        if os.name == "nt" or not pid or pid <= 0:
            return
        try:
            os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            pass
        except Exception:
            pass

    def _stop_process_record(self, record: dict, timeout: int = 10) -> bool:
        pid = int(record.get("pid", -1))
        if not self._is_pid_running(pid):
            return True

        if os.name == "nt":
            try:
                proc = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=max(5, timeout),
                )
                return proc.returncode == 0 or not self._is_pid_running(pid)
            except Exception:
                return not self._is_pid_running(pid)

        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass

        deadline = time.time() + max(1, timeout)
        while time.time() < deadline:
            self._reap_child_if_possible(pid)
            if not self._is_pid_running(pid):
                return True
            time.sleep(0.2)

        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
        time.sleep(0.3)
        self._reap_child_if_possible(pid)
        return not self._is_pid_running(pid)

    # -------- URL, screenshot, and health helpers --------
    def _validate_localhost_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise PermissionError("Only http/https localhost URLs are allowed")
        if not self._is_localhost_hostname(parsed.hostname):
            raise PermissionError("Only localhost, 127.0.0.1, or ::1 URLs are allowed")
        if parsed.username or parsed.password:
            raise PermissionError("Credentials in URLs are not allowed")

    def _is_localhost_hostname(self, hostname: str) -> bool:
        if not hostname:
            return False
        return hostname.lower().strip("[]") in LOCALHOST_NAMES

    def _check_localhost_url(self, url: str, timeout_sec: int = 5) -> dict:
        self._validate_localhost_url(url)
        started = time.time()
        try:
            req = Request(url, method="GET", headers={"User-Agent": "MCP-Local-QA/1.0"})
            with urlopen(req, timeout=timeout_sec) as resp:
                return {
                    "ok": True,
                    "status_code": getattr(resp, "status", None),
                    "elapsed_ms": int((time.time() - started) * 1000),
                }
        except HTTPError as e:
            # An HTTP error still proves the server answered.
            return {
                "ok": True,
                "status_code": e.code,
                "elapsed_ms": int((time.time() - started) * 1000),
                "http_error": True,
            }
        except URLError as e:
            return {
                "ok": False,
                "error": str(e.reason),
                "elapsed_ms": int((time.time() - started) * 1000),
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "elapsed_ms": int((time.time() - started) * 1000),
            }

    def _wait_for_localhost_url(self, url: str, timeout_sec: int = 30) -> dict:
        deadline = time.time() + max(1, timeout_sec)
        last = None
        while time.time() < deadline:
            last = self._check_localhost_url(url, timeout_sec=3)
            if last.get("ok"):
                last["ready"] = True
                return last
            time.sleep(0.8)
        return {
            "ready": False,
            "last_check": last,
            "message": f"URL did not become ready within {timeout_sec}s",
        }

    def _default_screenshot_path(self, url: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        parsed = urlparse(url)
        path_part = parsed.path.strip("/") or "root"
        if parsed.query:
            path_part += "-" + parsed.query
        slug = self._slugify(f"{parsed.hostname}-{parsed.port or ''}-{path_part}")
        day = datetime.now().strftime("%Y-%m-%d")
        return f"{DEFAULT_SCREENSHOT_DIR}/{day}/{stamp}-{slug}.png"

    def _default_log_path(self, name: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{DEFAULT_LOG_DIR}/{stamp}-{self._slugify(name)}.log"

    def _normalize_viewport(self, viewport: dict) -> dict:
        if not isinstance(viewport, dict):
            return dict(DEFAULT_VIEWPORT)
        width = int(viewport.get("width", DEFAULT_VIEWPORT["width"]))
        height = int(viewport.get("height", DEFAULT_VIEWPORT["height"]))
        width = max(320, min(width, 3840))
        height = max(240, min(height, 2160))
        return {"width": width, "height": height}

    def _safe_process_name(self, name: str) -> str:
        name = self._slugify(name or "default")
        return name or "default"

    def _slugify(self, text: str) -> str:
        text = str(text or "").lower()
        out = []
        for ch in text:
            if ch.isalnum():
                out.append(ch)
            elif ch in {"-", "_", "."}:
                out.append(ch)
            else:
                out.append("-")
        slug = "".join(out).strip("-._")
        while "--" in slug:
            slug = slug.replace("--", "-")
        return slug[:120] or "item"

    # -------- command and path security --------
    def _parse_command(self, cmd):
        if isinstance(cmd, str):
            argv = shlex.split(cmd)
        elif isinstance(cmd, list):
            if not all(isinstance(x, str) for x in cmd):
                raise ValueError("command array must contain only strings")
            argv = cmd
        else:
            raise ValueError("command must be string or array of strings")
        if not argv:
            raise ValueError("command cannot be empty")
        return argv

    def validate_path(self, user_path: str) -> Path:
        if user_path is None:
            raise ValueError("Path is required")
        abs_path = Path(user_path).resolve() if os.path.isabs(str(user_path)) else (self.allowed_directory / str(user_path)).resolve()
        try:
            abs_path.relative_to(self.allowed_directory)
        except ValueError:
            raise PermissionError("Path outside allowed directory")
        return abs_path


def create_handler(allowed_directory: Path, auth_token: str | None = None):
    def handler(*args, **kwargs):
        return MCPSSEHandler(allowed_directory, auth_token, *args, **kwargs)
    return handler


def main():
    parser = argparse.ArgumentParser(description="Token-protected MCP filesystem server with localhost QA tools.")
    parser.add_argument("directory_path", help="Allowed project/repo directory path")
    parser.add_argument("--host", default=os.environ.get("MCP_QA_HOST", "localhost"), help="Bind host. Default: localhost")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCP_QA_PORT", "8008")), help="Bind port. Default: 8008")
    parser.add_argument("--token", default=os.environ.get("MCP_QA_TOKEN", ""), help="MCP access token. Can also use MCP_QA_TOKEN env var")
    parser.add_argument("--no-token", action="store_true", help="Disable token protection. Do not use with ngrok/public tunnels.")
    args = parser.parse_args()

    allowed_directory = Path(args.directory_path).resolve()
    if not allowed_directory.exists() or not allowed_directory.is_dir():
        print(f"Error: {allowed_directory} is not a valid directory")
        sys.exit(1)

    auth_token = "" if args.no_token else (args.token or "").strip()
    token_suffix = f"?token={auth_token}" if auth_token else ""

    print(f"Starting MCP server restricted to: {allowed_directory}")
    print(f"Server URL: http://{args.host}:{args.port}")
    print(f"SSE URL for ChatGPT: http://{args.host}:{args.port}/sse/{token_suffix}")
    print(f"Token protection: {'enabled' if auth_token else 'disabled'}")
    print("QA tools enabled: start_localhost, localhost_status, stop_localhost, capture_web_screenshot, capture_web_screenshot_batch")

    with HTTPServer((args.host, args.port), create_handler(allowed_directory, auth_token)) as server:
        print("Server started. Use Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")


if __name__ == "__main__":
    main()
