# Releases

## Release tag

```text
v1.4.0
```

## Release title

```text
MCP Localhost QA Starter v1.4.0
```

## GitHub release description

```markdown
# MCP Localhost QA Starter v1.4.0

This is the first public-ready release of MCP Localhost QA Starter, a token-protected local MCP server that allows MCP-compatible AI clients to review, verify, and QA a local project or repository.

It is designed for developer QA, architecture review, code inspection, localhost testing, screenshot evidence capture, and controlled repo-level file operations.

## What this release includes

- Filesystem review tools:
  - `search`
  - `fetch`
  - `write_file`
  - `create_directory`
  - `delete_file`

- Codex-style workflow tools:
  - `shell`
  - `apply_patch`

- Localhost QA tools:
  - `start_localhost`
  - `localhost_status`
  - `stop_localhost`

- Browser evidence tools powered by Playwright:
  - `capture_web_screenshot`
  - `capture_web_screenshot_batch`

- Token-protected MCP access for local and tunneled usage
- WSL/Linux virtual environment support with `--venv`
- Automatic Playwright package check and Chromium verification
- Optional fixed token support using `--token` or `MCP_QA_TOKEN`
- Systemd service example for WSL/Linux
- Windows starter batch file included

## Main v1.4 improvements

### Hardened `delete_file`

The `delete_file` tool has been improved for safer and more compatible AI-agent usage.

It now accepts:

- `path`
- `id`
- `file_id`
- `target`
- `paths[]`

It also supports:

- `file://` URLs from search/fetch results
- Repo-root-style paths such as `/docs/file.txt`
- Multiple delete targets in one request
- Per-path delete details and errors
- Verification that deleted paths no longer exist

### Better service token behavior

The systemd service example now includes `--token ${MCP_QA_TOKEN}` so service restarts keep the same fixed token instead of generating a new one.

## Security model

This MCP server is designed to run locally and expose only the selected project/repo folder.

Security boundaries include:

- Filesystem paths are restricted to the selected workspace root
- Browser screenshot targets are restricted to localhost, `127.0.0.1`, or `::1`
- Screenshot and log paths are saved inside the selected workspace
- Token protection is enabled by default
- `--no-token` is available only for trusted local testing and should not be used with public tunnels

## Basic usage

```bash
python3 start_mcp_qa.py "/path/to/your/project"
```

With a virtual environment:

```bash
python3 start_mcp_qa.py "/path/to/your/project" --venv "/path/to/venv" --remember-venv
```

For Linux/WSL dependency setup:

```bash
python3 start_mcp_qa.py "/path/to/your/project" --venv "/path/to/venv" --remember-venv --with-deps
```

The starter prints the MCP SSE URL:

```text
http://localhost:8008/sse/?token=YOUR_TOKEN
```

For ngrok or another secure tunnel, keep the same path and token after the public domain:

```text
https://YOUR-TUNNEL-DOMAIN/sse/?token=YOUR_TOKEN
```

## Recommended QA evidence folders

```text
docs/qa-evidence/<stage-or-smoke-test>/
docs/qa/evidence/screenshots/<stage>/
docs/qa/evidence/logs/
```

## Recommended use cases

- ChatGPT-assisted local project review
- AI code review with controlled filesystem access
- Codex-style patch workflows
- Localhost UI QA
- Browser screenshot evidence capture
- Development milestone verification
- PRD-to-code review
- QA evidence collection for teams, business analysts, developers, and system architects

## Important note

This tool gives MCP-compatible AI clients controlled access to local development workflows. Review the security model before exposing it through any public tunnel. Keep token protection enabled for remote or tunneled usage.
```
