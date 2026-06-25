# Changelog

## v1.4.0

### Added

- Token-protected MCP localhost QA starter workflow
- Filesystem tools:
  - `search`
  - `fetch`
  - `write_file`
  - `create_directory`
  - `delete_file`
- Codex-style tools:
  - `shell`
  - `apply_patch`
- Localhost QA tools:
  - `start_localhost`
  - `localhost_status`
  - `stop_localhost`
- Browser evidence tools:
  - `capture_web_screenshot`
  - `capture_web_screenshot_batch`
- Playwright package check and Chromium verification
- WSL/Linux virtual environment selection with `--venv`
- `--remember-venv` support
- Fixed token support through `--token`
- Environment token support through `MCP_QA_TOKEN`
- Systemd service example
- Windows batch starter

### Changed

- `delete_file` now accepts `path`, `id`, `file_id`, `target`, and `paths[]`.
- `delete_file` now accepts `file://` URLs that resolve inside the workspace.
- `delete_file` now treats repo-root-style paths such as `/docs/file.txt` as workspace-relative paths when appropriate.
- `delete_file` now returns per-path delete details and errors.
- `delete_file` now verifies that deleted paths no longer exist.
- Systemd example now passes a fixed token so service restarts keep the same token.

### Security

- Token protection is enabled by default.
- Localhost browser screenshots are restricted to localhost targets.
- Filesystem paths are restricted to the selected workspace root.
- Screenshot and log paths are saved inside the selected workspace.

### Upgrade notes

Replace the previous files with the v1.4.0 files and restart the MCP server or systemd service.

```bash
systemctl restart mcp-server.service
systemctl status mcp-server.service
```

Confirm the running version:

```bash
curl -s "http://localhost:8008/?token=$MCP_QA_TOKEN" | python3 -m json.tool
```

Expected version:

```json
"version": "1.4.0"
```
