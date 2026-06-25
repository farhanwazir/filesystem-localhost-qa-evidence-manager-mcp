# QA Smoke-Test Prompts

## Filesystem tools

```text
Use only temporary files under docs/qa-evidence/mcp-smoke-test/. Test search, fetch, write_file, create_directory, and delete_file. Do not modify real project files. Report each tool call result and confirm whether deleted test files have exists_after: false.
```

## delete_file v1.4 regression test

```text
Retest only the delete_file tool using temporary files under docs/qa-evidence/mcp-smoke-test-v1-4/. Test path, id, file_id, target, repo-root-style path, file:// URL, and paths[] deletion. Do not modify real project files. Report whether each deleted file has exists_after: false.
```

## Localhost QA

```text
Start the project localhost server using the documented dev command. Check localhost status. Capture screenshots of the home page and one main app route. Save evidence under docs/qa/evidence/screenshots/local-smoke-test/. Stop the localhost server when done.
```

## PRD review

```text
Search for PRD, architecture, and route files. Compare the implementation against the PRD expectations. Do not modify files. Produce a gap report with exact file references and recommended next steps.
```

## Documentation review

```text
Review README, setup instructions, examples, and security documentation. Do not modify files. Report missing installation steps, unclear assumptions, and risky instructions.
```
