# systemd Service Example

Create a fixed token:

```bash
MCP_QA_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
printf 'MCP_QA_TOKEN=%s\n' "$MCP_QA_TOKEN" > /etc/mcp-localhost-qa.env
chmod 600 /etc/mcp-localhost-qa.env
```

Copy the service file:

```bash
cp examples/systemd-mcp-localhost-qa.service /etc/systemd/system/mcp-localhost-qa.service
```

Edit paths in the service file before starting.

Reload and start:

```bash
systemctl daemon-reload
systemctl enable mcp-localhost-qa.service
systemctl restart mcp-localhost-qa.service
systemctl status mcp-localhost-qa.service
```

Test:

```bash
source /etc/mcp-localhost-qa.env
curl -i "http://localhost:8008/?token=$MCP_QA_TOKEN"
```
