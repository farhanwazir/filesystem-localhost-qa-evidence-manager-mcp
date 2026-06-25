# Gemini CLI Setup Notes

Use this project with Gemini CLI or any MCP-compatible client that can launch local MCP servers or connect to SSE endpoints.

## Local command pattern

```json
{
  "mcpServers": {
    "mcp-localhost-qa": {
      "command": "python3",
      "args": [
        "/absolute/path/to/start_mcp_qa.py",
        "/absolute/path/to/your/project",
        "--venv",
        "/absolute/path/to/venv",
        "--remember-venv"
      ]
    }
  }
}
```

## SSE endpoint pattern

```text
http://localhost:8008/sse/?token=YOUR_TOKEN
```

## Recommended prompt

```text
Inspect the connected local project through MCP. Summarize the project structure, likely stack, entry points, test commands, and risks. Do not modify files.
```
