# Cursor Setup Notes

Use this repository as a local MCP server for Cursor or other MCP-compatible IDE clients.

## Recommended setup pattern

1. Start the MCP server locally.
2. Copy the printed SSE URL.
3. Add the MCP server to your IDE MCP settings if SSE MCP endpoints are supported.
4. Keep token protection enabled.

Example SSE URL:

```text
http://localhost:8008/sse/?token=YOUR_TOKEN
```

## Recommended prompt

```text
Use the MCP localhost QA tools to inspect the current repo. Do not modify files. Create a review summary with architecture, code quality, missing docs, and test coverage observations.
```

## Safety recommendation

Expose only the active project folder, not your full development directory.
