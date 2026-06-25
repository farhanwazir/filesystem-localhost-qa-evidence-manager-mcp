# Contributing

Thank you for your interest in contributing to MCP Localhost QA Starter.

This project is a local developer QA tool that gives MCP-compatible AI clients controlled access to project files, shell verification, localhost QA, and browser screenshot evidence.

## Before contributing

Please read:

- `README.md`
- `SECURITY.md`
- `CHANGELOG.md`

Security-sensitive changes should be handled carefully because this project can interact with local files and shell commands.

## Good contribution areas

Useful contributions include:

- Safer tool behavior
- Better path validation
- Better token handling
- More MCP client examples
- Improved Windows/macOS/Linux setup docs
- Better QA evidence workflows
- Tests for filesystem and delete behavior
- More robust localhost process handling
- Better Playwright screenshot options
- Documentation improvements

## Pull request expectations

A good pull request should include:

1. Clear summary of the change
2. Why the change is needed
3. Security impact, if any
4. Testing performed
5. Updated documentation, if behavior changed

## Development safety rules

When testing locally:

- Use a temporary project folder
- Do not expose sensitive directories
- Keep token protection enabled
- Use test files under `docs/qa-evidence/`
- Avoid destructive shell commands
- Review generated screenshots before sharing them

## Suggested test folder

```text
docs/qa-evidence/contribution-smoke-test/
```

## Code style

- Keep code simple and explicit
- Prefer clear validation over assumptions
- Fail loudly on unsafe or ambiguous inputs
- Keep filesystem operations restricted to the workspace root
- Keep localhost screenshot restrictions intact
- Avoid introducing external network access unless it is explicitly documented and controlled

## Reporting security issues

Do not open public issues with vulnerability details. See `SECURITY.md`.
