# QA Evidence Workflow

Use repo-local evidence folders so every AI-assisted QA session leaves an auditable trail.

## Recommended folders

```text
docs/qa-evidence/<stage-or-smoke-test>/
docs/qa/evidence/screenshots/<stage>/
docs/qa/evidence/logs/
```

## Suggested evidence structure

```text
docs/qa-evidence/
  mcp-smoke-test-v1-4/
    report.md
    files/
    screenshots/
    logs/
```

## Suggested report format

```markdown
# QA Evidence Report

## Scope

## Tools used

## Files inspected

## Commands run

## Screenshots captured

## Findings

## Risks

## Recommended next steps
```

## Safe testing rule

Create temporary files only under the active evidence folder. Do not modify real project files during smoke tests.
