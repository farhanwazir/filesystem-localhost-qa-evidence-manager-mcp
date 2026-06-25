# MCP Localhost QA Starter v1.4

This package starts a token-protected MCP server for ChatGPT QA review against a local project/repo.

It supports:

- Filesystem review tools: `search`, `fetch`, `write_file`, `create_directory`, `delete_file`
- Shell verification: `shell`
- Patch tool: `apply_patch`
- Localhost QA tools: `start_localhost`, `localhost_status`, `stop_localhost`
- Browser evidence tools: `capture_web_screenshot`, `capture_web_screenshot_batch`
- Built-in token protection for ngrok / remote access
- WSL/Linux virtual environment selection with `--venv`

## Files

Keep these files together in one folder:

```text
src/fileSystemMCP_localhost_QA.py
src/start_mcp_qa.py
scripts/start_mcp_qa_windows.bat
README_MCP_QA_STARTER.md
```

Do not place them inside the venv `bin/` folder. Keep the venv as a sibling folder or any separate folder.

## Recommended WSL usage

```bash
python3 /mnt/c/laragon/www/chatgpt_localfile_mcp/FileSystem-MCP-for-GPT/src/start_mcp_qa.py \
  "/mnt/c/laragon/www/MS-SaaSPlatform" \
  --venv "/mnt/c/laragon/www/chatgpt_localfile_mcp/FileSystem-MCP-for-GPT/venv" \
  --remember-venv \
  --with-deps
```

After the first run, if the venv was remembered:

```bash
python3 /mnt/c/laragon/www/chatgpt_localfile_mcp/FileSystem-MCP-for-GPT/start_mcp_qa.py \
  "/mnt/c/laragon/www/MS-SaaSPlatform"
```

## Token behavior

Token protection is enabled by default.

Token source priority:

1. `--token "your-fixed-token"`
2. `MCP_QA_TOKEN` environment variable
3. Auto-generated temporary token

The starter prints the local SSE URL:

```text
http://localhost:8008/sse/?token=YOUR_TOKEN
```

With ngrok, use:

```text
https://YOUR-NGROK-DOMAIN.ngrok-free.app/sse/?token=YOUR_TOKEN
```

## Systemd service example for WSL/Linux

Create a fixed token:

```bash
MCP_QA_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
printf 'MCP_QA_TOKEN=%s\n' "$MCP_QA_TOKEN" > /etc/mcp-server.env
chmod 600 /etc/mcp-server.env
```

Service file:

```ini
[Unit]
Description=FileSystem MCP Server with Localhost QA Tools
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/mnt/c/laragon/www/chatgpt_localfile_mcp/FileSystem-MCP-for-GPT
EnvironmentFile=/etc/mcp-server.env
ExecStart=/mnt/c/laragon/www/chatgpt_localfile_mcp/FileSystem-MCP-for-GPT/venv/bin/python /mnt/c/laragon/www/chatgpt_localfile_mcp/FileSystem-MCP-for-GPT/start_mcp_qa.py /mnt/c/laragon/www/MS-SaaSPlatform --venv /mnt/c/laragon/www/chatgpt_localfile_mcp/FileSystem-MCP-for-GPT/venv --server-file /mnt/c/laragon/www/chatgpt_localfile_mcp/FileSystem-MCP-for-GPT/fileSystemMCP_localhost_QA.py --host localhost --port 8008 --with-deps --token ${MCP_QA_TOKEN}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Reload/start:

```bash
systemctl daemon-reload
systemctl enable mcp-server.service
systemctl restart mcp-server.service
systemctl status mcp-server.service
```

## Testing token protection

Without token should return 401:

```bash
curl -i "http://localhost:8008/"
```

With token should return 200:

```bash
source /etc/mcp-server.env
curl -i "http://localhost:8008/?token=$MCP_QA_TOKEN"
```

Test tool listing:

```bash
curl -s -X POST "http://localhost:8008/sse/?token=$MCP_QA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 -m json.tool
```

## v1.4 fixes

- `delete_file` now accepts `path`, `id`, `file_id`, `target`, and `paths[]`.
- `delete_file` now accepts `file://` URLs that resolve inside the workspace.
- `delete_file` now treats repo-root style paths such as `/docs/file.txt` as `docs/file.txt` when they are not real absolute paths inside the workspace.
- `delete_file` now returns per-path delete details and errors instead of silently passing unclear inputs.
- Systemd example now includes `--token ${MCP_QA_TOKEN}` so service restarts keep the fixed token.

## v1.3 fixes

- `apply_patch` now supports Codex-style add/update/delete blocks and unified hunks.
- Unsupported patch shapes fail loudly instead of writing patch text into files.
- Screenshot navigation now defaults to `domcontentloaded` instead of `networkidle`, which avoids timeouts on live-reload servers like MkDocs/Vite.
- Screenshot tools accept optional `wait_until`: `domcontentloaded`, `load`, or `networkidle`.

## Recommended QA evidence folder

Use repo-local paths such as:

```text
docs/qa-evidence/<stage-or-smoke-test>/
docs/qa/evidence/screenshots/<stage>/
```

All paths are restricted to the allowed project root.
