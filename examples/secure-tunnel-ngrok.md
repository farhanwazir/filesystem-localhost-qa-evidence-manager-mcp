# Secure Tunnel Example

Use a tunnel only when your MCP client cannot reach your local server directly.

## Start the MCP server

```bash
export MCP_QA_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"

python3 start_mcp_qa.py "/path/to/your/project" \
  --token "$MCP_QA_TOKEN"
```

## Start ngrok

```bash
ngrok http 8008
```

## Use the tunneled SSE URL

```text
https://YOUR-NGROK-DOMAIN.ngrok-free.app/sse/?token=YOUR_TOKEN
```

## Important safety notes

- Keep token protection enabled.
- Do not use `--no-token`.
- Do not publish the tunnel URL.
- Rotate the token after demos or screen recordings.
- Stop the tunnel when finished.
