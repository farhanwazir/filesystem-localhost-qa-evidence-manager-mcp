# ChatGPT SSE URL Example

Start the server:

```bash
python3 start_mcp_qa.py "/path/to/your/project"
```

The starter prints an SSE URL:

```text
http://localhost:8008/sse/?token=YOUR_TOKEN
```

For a secure tunnel, keep the same path and token:

```text
https://YOUR-TUNNEL-DOMAIN/sse/?token=YOUR_TOKEN
```

Use the printed URL in any ChatGPT or MCP connector flow that accepts SSE MCP endpoints.

## Recommended first prompt

```text
Use the connected MCP localhost QA tools to inspect the project structure only. Do not modify files. Report the root folders, key files, likely stack, and any immediate documentation or security gaps.
```

## Safe smoke-test prompt

```text
Use only temporary files under docs/qa-evidence/mcp-smoke-test/. Test search, fetch, write_file, create_directory, delete_file, and report whether each operation succeeded. Do not modify real project files.
```
