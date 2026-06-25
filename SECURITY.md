# Security Policy

MCP Localhost QA Starter gives MCP-compatible AI clients controlled access to a selected local project folder. Because the server can expose files, run shell commands, apply patches, start localhost processes, and capture browser screenshots, it must be treated as a sensitive local development tool.

## Supported versions

| Version | Supported |
|---|---|
| 1.4.x | Yes |
| < 1.4.0 | No |

Older versions should be upgraded because v1.4.0 includes stronger `delete_file` handling and improved token persistence examples.

## Security model

The server is designed with these core boundaries:

- Filesystem operations are restricted to the selected workspace root.
- Browser screenshots are restricted to localhost targets only:
  - `localhost`
  - `127.0.0.1`
  - `::1`
- Screenshot and log files are resolved inside the selected workspace.
- Token protection is enabled by default.
- The starter can use a fixed token from `--token` or `MCP_QA_TOKEN`.
- `--no-token` is only for trusted local testing and must not be used with public tunnels.

## What this project protects against

The project is designed to reduce the risk of:

- Accidental file access outside the selected workspace
- Browser screenshot access to non-localhost URLs
- Unauthenticated access when token protection is enabled
- Ambiguous delete operations from AI clients
- Long-running localhost process confusion through registered process tracking

## What this project does not fully protect against

This project does not guarantee protection from:

- Malicious prompts sent to an authorized MCP client
- A compromised local machine
- A leaked MCP token
- Dangerous shell commands approved by the user
- Public tunnel misconfiguration
- Sensitive data already present inside the selected project folder
- Third-party MCP client bugs or unsafe client behavior

## Required safe usage rules

Use these rules when running the server:

1. Expose only the project folder you want the AI client to review.
2. Keep token protection enabled.
3. Use a strong fixed token for long-running services.
4. Do not use `--no-token` with ngrok, Cloudflare Tunnel, SSH forwarding, or any public access method.
5. Do not expose your home directory, root drive, cloud credential folders, SSH folders, or password manager exports.
6. Review AI-suggested file changes before applying them.
7. Use temporary folders for smoke tests.
8. Keep QA screenshots and logs inside repo-local evidence folders.
9. Stop the server when not in use.
10. Rotate the token if you believe it was exposed.

## Recommended safe folder scope

Good:

```text
/path/to/specific-project
/path/to/repo
/mnt/c/laragon/www/my-project
```

Avoid:

```text
/
C:\
/home/username
/Users/username
~/.ssh
~/.aws
~/.config
```

## Public tunnel warning

When using a tunnel, always keep the token in the URL or Authorization header.

Example:

```text
https://YOUR-TUNNEL-DOMAIN/sse/?token=YOUR_TOKEN
```

Do not share tunnel URLs in screenshots, public issues, logs, support tickets, or videos unless the token is removed or rotated.

## Shell command risk

The `shell` tool can execute commands inside the selected workspace. It is intended for short verification commands such as:

```bash
python --version
npm test
pytest
composer test
php artisan test
```

Avoid using shell commands for destructive operations unless you fully understand the effect.

Examples of commands that require extra caution:

```bash
rm -rf
del /s
git reset --hard
git clean -fdx
docker system prune
npm install scripts from untrusted packages
```

## Patch risk

The `apply_patch` tool can modify files. Treat patches like code submitted by a developer:

- Review the diff
- Check affected files
- Run tests
- Commit only after human approval

## Screenshot privacy

Screenshots may contain:

- Project data
- Localhost application data
- Customer records
- API keys shown in UI
- Internal dashboards
- User profile data
- Admin screens

Before sharing screenshots publicly, inspect and redact sensitive information.

## Reporting a vulnerability

Please do not open a public GitHub issue with sensitive vulnerability details.

Preferred reporting methods:

1. Use GitHub private vulnerability reporting if enabled.
2. If private vulnerability reporting is not enabled, open a minimal public issue asking for a private security contact. Do not include exploit details, tokens, screenshots, or sensitive logs.
3. Include a clear summary, affected version, reproduction steps, and impact assessment in the private report.

## Security response expectations

For valid security reports, the maintainer should aim to:

- Acknowledge the report
- Confirm affected versions
- Prepare a fix or mitigation
- Publish a patched release
- Credit the reporter if requested and appropriate

## Token rotation

If a token may have leaked:

1. Stop the MCP server.
2. Generate a new token.
3. Restart the server with the new token.
4. Update the MCP client connection URL.
5. Delete or redact logs/screenshots containing the old token.

Example:

```bash
export MCP_QA_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python3 start_mcp_qa.py "/path/to/project" --token "$MCP_QA_TOKEN"
```

## Final recommendation

Run this server only in a trusted development environment, expose the smallest useful project folder, and keep human review in the loop for file modifications, patches, and shell commands.
