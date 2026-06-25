#!/usr/bin/env python3
"""
Starter for fileSystemMCP_localhost_QA.py

Purpose:
- Accept the project/repo location from a command argument or interactive prompt.
- Use a chosen MCP virtual environment when --venv is provided or remembered.
- Install the Python Playwright package only inside that selected environment.
- Install/verify the Chromium browser for Playwright.
- Start the token-protected MCP localhost QA server restricted to the selected project folder.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import secrets
import subprocess
import sys
from pathlib import Path

MIN_PYTHON = (3, 9)
SERVER_FILENAME = "fileSystemMCP_localhost_QA.py"
CONFIG_DIR = Path.home() / ".mcp-localhost-qa"
CONFIG_PATH = CONFIG_DIR / "starter-config.json"


def print_header(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def run_command(command: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(command)}")
    return subprocess.run(command, cwd=str(cwd) if cwd else None, check=check)


def ensure_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        version = ".".join(map(str, MIN_PYTHON))
        raise SystemExit(f"Python {version}+ is required. Current Python: {sys.version.split()[0]}")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def resolve_project_path(project_path_arg: str | None) -> Path:
    raw = project_path_arg
    if not raw:
        raw = input("Enter the full project/repo folder path to expose through MCP: ").strip().strip('"')

    if not raw:
        raise SystemExit("Project path is required.")

    project_path = Path(raw).expanduser().resolve()
    if not project_path.exists():
        raise SystemExit(f"Project path does not exist: {project_path}")
    if not project_path.is_dir():
        raise SystemExit(f"Project path is not a directory: {project_path}")
    return project_path


def resolve_server_file(server_file_arg: str | None) -> Path:
    if server_file_arg:
        server_file = Path(server_file_arg).expanduser().resolve()
    else:
        server_file = Path(__file__).resolve().parent / SERVER_FILENAME

    if not server_file.exists():
        raise SystemExit(
            f"MCP server file not found: {server_file}\n"
            f"Place {SERVER_FILENAME} in the same folder as this starter, "
            "or pass --server-file /path/to/fileSystemMCP_localhost_QA.py"
        )
    return server_file


def resolve_venv_python(venv_path: str | None) -> Path | None:
    if not venv_path:
        return None
    venv = Path(venv_path).expanduser().resolve()
    candidates = [venv / "bin" / "python", venv / "Scripts" / "python.exe"]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise SystemExit(f"Could not find Python executable inside venv: {venv}")


def same_executable(a: Path, b: Path) -> bool:
    try:
        return a.resolve().samefile(b.resolve())
    except Exception:
        return str(a.resolve()) == str(b.resolve())


def maybe_relaunch_in_venv(args: argparse.Namespace) -> None:
    config = load_config()
    venv_arg = args.venv or config.get("venv")

    if args.venv and args.remember_venv:
        config["venv"] = str(Path(args.venv).expanduser().resolve())
        save_config(config)
        print(f"Remembered MCP venv: {config['venv']}")

    venv_python = resolve_venv_python(venv_arg)
    if not venv_python:
        return

    current = Path(sys.executable).resolve()
    if same_executable(current, venv_python):
        return

    if os.environ.get("MCP_QA_VENV_RELAUNCHED") == "1":
        raise SystemExit(
            f"Tried to relaunch inside venv but current executable is still not expected.\n"
            f"Current: {current}\nExpected: {venv_python}"
        )

    print_header("Switching to selected MCP virtual environment")
    print(f"Current Python: {current}")
    print(f"MCP venv Python: {venv_python}")
    env = os.environ.copy()
    env["MCP_QA_VENV_RELAUNCHED"] = "1"
    os.execve(str(venv_python), [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]], env)


def package_installed(package_import_name: str) -> bool:
    return importlib.util.find_spec(package_import_name) is not None


def ensure_playwright_package(skip_install: bool, upgrade: bool) -> None:
    print_header("Checking Python dependency: playwright")

    if package_installed("playwright") and not upgrade:
        print("Playwright Python package is already installed in this Python environment.")
        return

    if skip_install:
        print("Dependency installation skipped by --skip-install.")
        return

    pip_cmd = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        pip_cmd.append("--upgrade")
    pip_cmd.append("playwright")
    run_command(pip_cmd)


def playwright_chromium_launches() -> bool:
    test_code = """
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    browser.close()
""".strip()
    proc = subprocess.run(
        [sys.executable, "-c", test_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode == 0:
        return True

    print("Chromium launch check failed. It may not be installed yet.")
    if proc.stderr:
        print(proc.stderr[-2000:])
    return False


def ensure_playwright_browser(skip_browser_install: bool, with_deps: bool) -> None:
    print_header("Checking Playwright browser: chromium")

    if not package_installed("playwright"):
        print("Playwright package is not installed, so browser check cannot run yet.")
        return

    if playwright_chromium_launches():
        print("Playwright Chromium is ready.")
        return

    if skip_browser_install:
        print("Browser installation skipped by --skip-browser-install.")
        return

    install_cmd = [sys.executable, "-m", "playwright", "install"]
    if with_deps:
        install_cmd.append("--with-deps")
    install_cmd.append("chromium")
    run_command(install_cmd)

    if not playwright_chromium_launches():
        raise SystemExit(
            "Playwright Chromium still could not launch after installation. "
            "Check the terminal error above. On Linux, try running again with --with-deps."
        )
    print("Playwright Chromium installed and verified.")


def resolve_token(args: argparse.Namespace) -> tuple[str, str]:
    if args.no_token:
        return "", "disabled"
    if args.token:
        return args.token.strip(), "provided by --token"
    env_token = os.environ.get("MCP_QA_TOKEN", "").strip()
    if env_token:
        return env_token, "provided by MCP_QA_TOKEN environment variable"
    return secrets.token_urlsafe(32), "generated automatically"


def start_mcp_server(server_file: Path, project_path: Path, args: argparse.Namespace, token: str, token_source: str) -> int:
    print_header("Starting MCP Localhost QA Server")
    print(f"Project/repo root: {project_path}")
    print(f"MCP server file:   {server_file}")
    print(f"Bind address:      {args.host}:{args.port}")
    print(f"Token protection:  {'enabled, ' + token_source if token else 'disabled'}")

    local_sse = f"http://{args.host}:{args.port}/sse/"
    if token:
        local_sse += f"?token={token}"
        print(f"\nMCP token:\n{token}")
    print(f"\nChatGPT SSE URL:\n{local_sse}")
    print("\nFor ngrok, keep the same /sse/?token=... path after the ngrok domain.")
    print("Keep this terminal/service running while ChatGPT is connected.\n")

    command = [
        sys.executable,
        str(server_file),
        str(project_path),
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.no_token:
        command.append("--no-token")

    env = os.environ.copy()
    if token:
        env["MCP_QA_TOKEN"] = token

    try:
        proc = subprocess.run(command, cwd=str(server_file.parent), env=env)
        return int(proc.returncode or 0)
    except KeyboardInterrupt:
        print("\nStarter stopped by user.")
        return 130


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install required QA dependencies and start the token-protected MCP localhost QA server."
    )
    parser.add_argument("project_path", nargs="?", help="Project/repo folder to expose through MCP.")
    parser.add_argument("--server-file", help="Path to fileSystemMCP_localhost_QA.py. Defaults to same folder as this starter.")
    parser.add_argument("--venv", help="Path to the MCP Python virtual environment to use.")
    parser.add_argument("--remember-venv", action="store_true", help="Save --venv for future starter runs.")
    parser.add_argument("--skip-install", action="store_true", help="Do not install missing Python packages.")
    parser.add_argument("--skip-browser-install", action="store_true", help="Do not install Playwright Chromium browser binaries.")
    parser.add_argument("--upgrade", action="store_true", help="Upgrade Playwright package instead of only installing when missing.")
    parser.add_argument("--with-deps", action="store_true", help="Pass --with-deps to playwright install chromium. Useful on Linux/WSL.")
    parser.add_argument("--host", default=os.environ.get("MCP_QA_HOST", "localhost"), help="MCP bind host. Default: localhost.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCP_QA_PORT", "8008")), help="MCP bind port. Default: 8008.")
    parser.add_argument("--token", help="Fixed MCP token. If omitted, MCP_QA_TOKEN env var is used; otherwise one is generated.")
    parser.add_argument("--no-token", action="store_true", help="Disable token protection. Do not use with ngrok/public tunnels.")
    return parser.parse_args()


def main() -> int:
    ensure_python_version()
    args = parse_args()
    maybe_relaunch_in_venv(args)

    project_path = resolve_project_path(args.project_path)
    server_file = resolve_server_file(args.server_file)
    token, token_source = resolve_token(args)

    print_header("MCP QA Starter")
    print(f"Python:     {sys.version.split()[0]}")
    print(f"Platform:   {platform.platform()}")
    print(f"Executable: {sys.executable}")

    ensure_playwright_package(skip_install=args.skip_install, upgrade=args.upgrade)
    ensure_playwright_browser(skip_browser_install=args.skip_browser_install, with_deps=args.with_deps)
    return start_mcp_server(server_file, project_path, args, token, token_source)


if __name__ == "__main__":
    raise SystemExit(main())
