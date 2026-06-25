# Codex Workflow Example

MCP Localhost QA Starter exposes Codex-style tools such as:

- `shell`
- `apply_patch`

## Safe review prompt

```text
Review this repository using MCP filesystem tools. Do not modify files. Identify architecture risks, missing tests, and unclear setup instructions. Use shell only for non-destructive verification commands.
```

## Controlled patch prompt

```text
Prepare a small patch for the issue you found. Keep the change minimal. Explain the diff before applying it. After applying, run only the relevant tests.
```

## Recommended shell commands

Use short verification commands:

```bash
python --version
node --version
npm test
pytest
php artisan test
composer test
```

Avoid destructive commands unless manually approved.
