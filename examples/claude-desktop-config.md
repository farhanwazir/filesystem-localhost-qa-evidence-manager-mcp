# Claude Desktop Local Config Example

This is a generic local server pattern. Adjust the command and paths for your operating system.

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

For Windows:

```json
{
  "mcpServers": {
    "mcp-localhost-qa": {
      "command": "py",
      "args": [
        "C:\\path\\to\\start_mcp_qa.py",
        "C:\\path\\to\\your\\project"
      ]
    }
  }
}
```

Keep the exposed project path as narrow as possible.
