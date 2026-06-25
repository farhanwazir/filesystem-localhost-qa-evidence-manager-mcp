# MCP Local Filesystem + Localhost QA Server

A practical Model Context Protocol (MCP) server package for local repository review, developer QA, browser screenshot evidence, and AI-assisted codebase inspection across ChatGPT, Codex, Claude, Cursor, and Gemini-compatible workflows.

> **Status:** v1.4 starter documentation  
> **Audience:** developers, system architects, business analysts, QA reviewers, AI coding workflow owners, and technical project managers  
> **Primary use case:** expose one trusted local project folder to an AI MCP client so the AI can inspect files, run controlled local commands, start local dev servers, capture localhost screenshots, and save QA evidence inside the project.

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [Terminology](#terminology)
3. [Who This Is Best For](#who-this-is-best-for)
4. [What Is Included](#what-is-included)
5. [Architecture Overview](#architecture-overview)
6. [Tool Groups](#tool-groups)
7. [Local Filesystem vs Localhost QA vs QA Evidence](#local-filesystem-vs-localhost-qa-vs-qa-evidence)
8. [Security Model](#security-model)
9. [System Requirements](#system-requirements)
10. [Recommended Repository Layout](#recommended-repository-layout)
11. [Installation: Universal Steps](#installation-universal-steps)
12. [Windows Setup](#windows-setup)
13. [Linux Setup](#linux-setup)
14. [macOS Setup](#macos-setup)
15. [WSL Setup](#wsl-setup)
16. [Using a Python Virtual Environment](#using-a-python-virtual-environment)
17. [Configuration Reference](#configuration-reference)
18. [Starting the MCP Server](#starting-the-mcp-server)
19. [Token Protection](#token-protection)
20. [Testing the Server](#testing-the-server)
21. [Using With ChatGPT](#using-with-chatgpt)
22. [Using With OpenAI Codex](#using-with-openai-codex)
23. [Using With Claude / Claude Desktop / Claude Code](#using-with-claude--claude-desktop--claude-code)
24. [Using With Cursor](#using-with-cursor)
25. [Using With Gemini CLI](#using-with-gemini-cli)
26. [Recommended Prompt Patterns](#recommended-prompt-patterns)
27. [QA Evidence Workflow](#qa-evidence-workflow)
28. [Example Developer Workflows](#example-developer-workflows)
29. [Business Analyst and System Architect Workflows](#business-analyst-and-system-architect-workflows)
30. [Extensions and Recommended Add-ons](#extensions-and-recommended-add-ons)
31. [Troubleshooting](#troubleshooting)
32. [Known Limitations](#known-limitations)
33. [Production Hardening Roadmap](#production-hardening-roadmap)
34. [Recommended GitHub Files](#recommended-github-files)
35. [Glossary](#glossary)
36. [References](#references)

---

## What This Project Does

This package starts a token-protected local MCP server that is restricted to one chosen project or repository folder. Once connected to an MCP client, the AI can use structured tools to inspect and operate inside that allowed workspace.

The package is designed for local development and QA review, not public production hosting.

It helps an AI assistant answer questions such as:

- “Show me all files in this repo.”
- “Read the PRD and compare it against the implementation.”
- “Search for payment gateway usage.”
- “Run the test suite.”
- “Start the local Vite/Laravel/MkDocs app.”
- “Capture screenshots from localhost pages.”
- “Save QA screenshots and logs under `docs/qa/evidence/`.”
- “Patch a file only after I approve the change.”

---

## Terminology

### MCP

**Model Context Protocol** is an open protocol for connecting AI applications to external systems such as local files, databases, APIs, tools, workflows, prompts, and business systems.

### MCP host

The application the user interacts with, such as ChatGPT, Claude Desktop, Cursor, Gemini CLI, or Codex.

### MCP client

The connector layer inside the host that talks to a specific MCP server.

### MCP server

A local or remote process that exposes tools, resources, or prompts to an AI host through MCP.

### Tool

A callable operation exposed by the MCP server. In this project, tools include file search, file fetch, shell command execution, local server start/stop, and screenshot capture.

### Localhost

A web server running on the same machine, usually accessed through `http://localhost:<port>` or `http://127.0.0.1:<port>`.

### QA evidence

Screenshots, logs, reports, terminal output, and test artifacts saved to a repository folder to prove what was reviewed and what passed or failed.

---

## Who This Is Best For

| User Type | Best Use | Why It Helps |
|---|---|---|
| Solo developer | Local repo inspection, patches, screenshots | Gives the AI controlled access to the real codebase and localhost UI. |
| Full-stack developer | Laravel, React, Vite, MkDocs, Docker, API testing | Can start dev servers, run tests, inspect files, and capture UI evidence. |
| System architect | Architecture review, code-to-PRD traceability, dependency review | Lets the AI verify actual files instead of relying on pasted summaries. |
| Business analyst | PRD compliance checks, acceptance criteria, workflow validation | Can inspect requirements docs and compare them with implemented surfaces. |
| QA engineer | Localhost smoke testing and screenshot evidence | Saves repeatable evidence under repo-local folders. |
| Technical project manager | Milestone verification and delivery acceptance | Produces grounded reports from actual project files. |
| Agency / client delivery teams | Auditable delivery review | Creates structured evidence before client handoff. |

### Not ideal for

- Untrusted public users.
- Multi-tenant public production access without additional authentication and authorization.
- Highly sensitive repositories unless strict local-only controls are enforced.
- Teams that want unattended write actions without human review.

---

## What Is Included

Keep these files together in one folder:

```text
src/fileSystemMCP_localhost_QA.py
src/start_mcp_qa.py
scripts/start_mcp_qa_windows.bat
README_MCP_QA_STARTER.md
README_MCP_QA_STARTER_v1_4.md
```

### `fileSystemMCP_localhost_QA.py`

The MCP server. It exposes filesystem, shell, patch, localhost process, and screenshot tools.

### `start_mcp_qa.py`

The recommended starter script. It:

- accepts the project/repo folder path,
- optionally switches into a selected virtual environment,
- installs/verifies the Python `playwright` package,
- installs/verifies the Chromium browser for Playwright,
- generates or uses a token,
- starts the MCP server restricted to the selected project root.

### `start_mcp_qa_windows.bat`

Windows convenience launcher. It calls:

```bat
python "%~dp0..\src\start_mcp_qa.py" %*
```

### README file

Short starter guide and version notes.

---

## Architecture Overview

```text
+---------------------------+
| AI Host / MCP Client      |
| ChatGPT / Codex / Claude  |
| Cursor / Gemini CLI       |
+-------------+-------------+
              |
              | MCP over HTTP/SSE or client adapter
              v
+-------------+-------------+
| Local MCP QA Server       |
| fileSystemMCP_localhost_QA|
| Token protected           |
+-------------+-------------+
              |
              | Restricted path validation
              v
+-------------+-------------+
| Allowed Project Root      |
| /path/to/your/repo        |
+------+------+-------------+
       |      |
       |      +----------------------+
       |                             |
       v                             v
Filesystem tools            Localhost QA tools
search/fetch/write          start/status/stop dev server
apply_patch/shell           capture screenshots/logs
```

The AI does not receive unrestricted access to your full machine. Every file operation is resolved inside the allowed project root. Browser screenshot tools are restricted to localhost URLs.

---

## Tool Groups

### Filesystem review tools

| Tool | Purpose |
|---|---|
| `search` | Search files and directories inside the allowed project root. |
| `fetch` | Read a file or directory listing. |
| `write_file` | Write a UTF-8 text file inside the project root. |
| `create_directory` | Create a directory inside the project root. |
| `delete_file` | Delete one or more files/directories inside the project root. |

### Developer execution tools

| Tool | Purpose |
|---|---|
| `shell` | Run short shell commands inside the allowed workspace. |
| `apply_patch` | Apply Codex-style file patches safely. |

### Localhost QA tools

| Tool | Purpose |
|---|---|
| `start_localhost` | Start a local dev server as a background process. |
| `localhost_status` | Check if the registered process and/or URL is healthy. |
| `stop_localhost` | Stop the registered local dev server. |

### Browser evidence tools

| Tool | Purpose |
|---|---|
| `capture_web_screenshot` | Capture one localhost screenshot using Playwright. |
| `capture_web_screenshot_batch` | Capture multiple localhost screenshots in one run. |

---

## Local Filesystem vs Localhost QA vs QA Evidence

### Local Filesystem

**Purpose:** Give an AI tool controlled access to a selected local project folder.

It is best for:

- code review,
- PRD comparison,
- file search,
- documentation review,
- small approved edits,
- repository structure analysis,
- configuration inspection,
- controlled patching.

Example prompt:

```text
Use the Local Filesystem tools to inspect the repository. Search for all payment gateway references, fetch the relevant files, and report whether the code violates the platform-only payment policy. Do not modify files.
```

### Localhost QA

**Purpose:** Let the AI start and check a local web application server for review.

It is best for:

- starting a Vite dev server,
- starting a Laravel local server,
- checking MkDocs/Docusaurus docs locally,
- smoke-testing routes,
- verifying rendered UI,
- validating admin panels or dashboards.

Example prompt:

```text
Start the local docs server using `mkdocs serve -a 127.0.0.1:8010`, wait until it is ready, then check the localhost status. Do not modify files.
```

### Localhost QA Evidence

**Purpose:** Save proof of what was tested, reviewed, or captured.

It is best for:

- QA sign-off,
- milestone acceptance,
- client handoff,
- sprint evidence,
- regression proof,
- audit-friendly delivery documentation.

Recommended paths:

```text
docs/qa-evidence/<stage-or-smoke-test>/
docs/qa/evidence/screenshots/<stage>/
docs/qa/evidence/logs/<stage>/
```

Example prompt:

```text
Create a QA evidence folder under docs/qa-evidence/stage-01-smoke/. Capture screenshots of the dashboard, login page, and settings page. Save a Markdown summary report in the same folder.
```

---

## Security Model

This project has a defensive local-first security model:

1. **Workspace root restriction**  
   All file paths must resolve inside the selected project folder.

2. **Localhost-only browser targets**  
   Screenshot tools only allow `localhost`, `127.0.0.1`, or `::1` HTTP/HTTPS URLs.

3. **Token protection**  
   Token protection is enabled by default. The starter can use a fixed token, environment token, or auto-generated token.

4. **Short shell command timeout**  
   `shell` is intended for short verification commands, not long-running servers.

5. **Separate localhost process registry**  
   Long-running local dev servers are tracked under `.mcp/runtime/localhost_processes.json`.

6. **Restricted environment cleanup**  
   The server removes common cloud credential variables from subprocess environments.

7. **No full-machine file access**  
   The server only exposes the folder you explicitly pass at startup.

### Important security rules

- Do not run this server against folders you do not trust.
- Do not expose it publicly without token protection.
- Do not use `--no-token` with ngrok, Cloudflare Tunnel, or any public tunnel.
- Do not paste generated tokens into public chats, screenshots, GitHub issues, or commits.
- Review every write action before approving it.
- Prefer read-only workflows for BA, architecture, and QA review.
- Keep `.mcp/runtime/`, `.env`, and virtual environment folders out of Git.

Recommended `.gitignore` entries:

```gitignore
# MCP runtime
.mcp/runtime/

# Python virtual environments
.venv/
venv/

# Secrets
.env
.env.*
*.key
*.pem

# Optional raw QA logs
# Keep selected screenshots/reports only if your team wants evidence committed.
docs/qa/evidence/logs/
```

---

## System Requirements

### Required

- Python 3.9+
- `pip`
- Network access for first-time package/browser installation
- A terminal/shell
- A project folder to expose

### Automatically handled by starter

The starter checks and installs:

- Python `playwright` package
- Playwright Chromium browser

### Optional

- `ngrok` or Cloudflare Tunnel for ChatGPT remote HTTPS access
- `systemd` for Linux/WSL persistent service
- `uv` for faster Python environment management
- Docker for reproducible deployment
- Git for versioned QA evidence and review reports

---

## Recommended Repository Layout

For GitHub publication, use this structure:

```text
mcp-localhost-qa/
├─ README.md
├─ LICENSE
├─ SECURITY.md
├─ CHANGELOG.md
├─ .gitignore
├─ .env.example
├─ src/
│  ├─ fileSystemMCP_localhost_QA.py
│  └─ start_mcp_qa.py
├─ scripts/
│  └─ start_mcp_qa_windows.bat
├─ docs/
│  ├─ installation.md
│  ├─ configuration.md
│  ├─ clients/
│  │  ├─ chatgpt.md
│  │  ├─ codex.md
│  │  ├─ claude.md
│  │  ├─ cursor.md
│  │  └─ gemini.md
│  ├─ qa-evidence-workflow.md
│  ├─ security-model.md
│  └─ troubleshooting.md
├─ examples/
│  ├─ cursor-mcp.json
│  ├─ gemini-settings.json
│  ├─ codex-config.toml
│  ├─ claude-desktop-config.json
│  └─ qa-prompts.md
└─ tests/
   ├─ test_delete_file.py
   ├─ test_path_validation.py
   ├─ test_token_auth.py
   └─ test_localhost_screenshot.py
```

For the current starter package, this repo uses a cleaner layout with separate source and script folders:

```text
FileSystem-MCP-for-GPT/
├─ src/
│  ├─ fileSystemMCP_localhost_QA.py
│  └─ start_mcp_qa.py
├─ scripts/
│  └─ start_mcp_qa_windows.bat
└─ README_MCP_QA_STARTER_v1_4.md
```

---

## Installation: Universal Steps

1. Create a folder for the MCP starter package.
2. Place these files inside it:

```text
fileSystemMCP_localhost_QA.py
start_mcp_qa.py
start_mcp_qa_windows.bat
README_MCP_QA_STARTER_v1_4.md
```

3. Create a virtual environment outside or beside the starter files.
4. Start the server with your project path.
5. Copy the printed SSE URL.
6. Add the URL to your MCP client.

---

## Windows Setup

### 1. Install Python

Install Python 3.9 or newer. During installation, enable:

```text
Add python.exe to PATH
```

Verify:

```powershell
python --version
pip --version
```

If `python` is not found, try:

```powershell
py --version
```

### 2. Create the MCP starter folder

Example:

```powershell
mkdir C:\mcp-tools\FileSystem-MCP-for-GPT
```

Place the package files in that folder.

### 3. Create a virtual environment

```powershell
cd C:\mcp-tools\FileSystem-MCP-for-GPT
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use either:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

or run with the venv Python directly:

```powershell
.\.venv\Scripts\python.exe --version
```

### 4. Start the MCP server

```powershell
.\start_mcp_qa_windows.bat "C:\path\to\your\project" --venv "C:\mcp-tools\FileSystem-MCP-for-GPT\.venv" --remember-venv
```

### 5. Copy the printed SSE URL

Example:

```text
http://localhost:8008/sse/?token=YOUR_TOKEN
```

Use this URL in your MCP client configuration.

---

## Linux Setup

### 1. Install Python and venv support

Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl
```

Fedora:

```bash
sudo dnf install -y python3 python3-pip
```

Arch:

```bash
sudo pacman -S python python-pip
```

### 2. Create a starter folder

```bash
mkdir -p ~/mcp-tools/FileSystem-MCP-for-GPT
cd ~/mcp-tools/FileSystem-MCP-for-GPT
```

Place the package files in this folder.

### 3. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 4. Start the server

Use `--with-deps` on Linux so Playwright can install needed browser dependencies:

```bash
python3 start_mcp_qa.py "/path/to/your/project" \
  --venv "$HOME/mcp-tools/FileSystem-MCP-for-GPT/.venv" \
  --remember-venv \
  --with-deps
```

---

## macOS Setup

### 1. Install Python

Using Homebrew:

```bash
brew install python
```

Verify:

```bash
python3 --version
pip3 --version
```

### 2. Create a starter folder

```bash
mkdir -p ~/mcp-tools/FileSystem-MCP-for-GPT
cd ~/mcp-tools/FileSystem-MCP-for-GPT
```

Place the package files in this folder.

### 3. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 4. Start the server

```bash
python3 start_mcp_qa.py "/Users/yourname/path/to/project" \
  --venv "$HOME/mcp-tools/FileSystem-MCP-for-GPT/.venv" \
  --remember-venv
```

---

## WSL Setup

WSL is recommended when your project uses Linux-native tooling but files live on Windows.

Example folder layout:

```text
/mnt/c/your-directory/FileSystem-MCP/
/mnt/c/your-project-directory/app/
```

First run:

```bash
python3 /mnt/c/your-directory/FileSystem-MCP/src/start_mcp_qa.py \
  "/mnt/c/your-project-directory/app" \
  --venv "/mnt/c/your-directory/FileSystem-MCP/venv" \
  --remember-venv \
  --with-deps
```

After the venv is remembered:

```bash
python3 /mnt/c/your-directory/FileSystem-MCP/start_mcp_qa.py \
  "/mnt/c/your-project-directory/app"
```

---

## Using a Python Virtual Environment

### Why use a venv?

Use a virtual environment to isolate MCP server dependencies from your system Python and from your application’s own dependencies.

This project uses Playwright for browser screenshots. The starter installs the Playwright Python package and Chromium browser into the selected environment.

### Recommended layout

```text
FileSystem-MCP-for-GPT/
├─ .venv/
├─ fileSystemMCP_localhost_QA.py
├─ start_mcp_qa.py
└─ start_mcp_qa_windows.bat
```

or:

```text
mcp-tools/
├─ venv/
└─ FileSystem-MCP-for-GPT/
   ├─ fileSystemMCP_localhost_QA.py
   └─ start_mcp_qa.py
```

Do not place the starter files inside the venv `bin/` or `Scripts/` directory.

### Remembering a venv

Use:

```bash
--remember-venv
```

The starter saves the selected venv path under:

```text
~/.mcp-localhost-qa/starter-config.json
```

Next time, you can omit `--venv` if you want to reuse the remembered environment.

---

## Configuration Reference

### Starter command

```bash
python start_mcp_qa.py <project_path> [options]
```

### Main options

| Option | Purpose |
|---|---|
| `<project_path>` | Project/repo folder to expose through MCP. |
| `--server-file` | Path to `fileSystemMCP_localhost_QA.py` if not beside the starter. |
| `--venv` | Path to the Python virtual environment. |
| `--remember-venv` | Save the venv path for future runs. |
| `--skip-install` | Do not install missing Python packages. |
| `--skip-browser-install` | Do not install Playwright browser binaries. |
| `--upgrade` | Upgrade Playwright package. |
| `--with-deps` | Install Playwright system dependencies; useful on Linux/WSL. |
| `--host` | Bind host. Default: `localhost`. |
| `--port` | Bind port. Default: `8008`. |
| `--token` | Fixed MCP token. |
| `--no-token` | Disable token protection. Do not use for public tunnels. |

### Environment variables

| Variable | Purpose |
|---|---|
| `MCP_QA_HOST` | Default bind host. |
| `MCP_QA_PORT` | Default bind port. |
| `MCP_QA_TOKEN` | Fixed token used by server and starter. |

---

## Starting the MCP Server

### Auto-generated token

```bash
python start_mcp_qa.py "/path/to/project" --venv "/path/to/venv" --remember-venv
```

The starter prints:

```text
MCP token:
YOUR_GENERATED_TOKEN

ChatGPT SSE URL:
http://localhost:8008/sse/?token=YOUR_GENERATED_TOKEN
```

### Fixed token

Linux/macOS:

```bash
export MCP_QA_TOKEN="replace-with-long-random-token"
python start_mcp_qa.py "/path/to/project" --venv "/path/to/venv"
```

Windows PowerShell:

```powershell
$env:MCP_QA_TOKEN="replace-with-long-random-token"
.\start_mcp_qa_windows.bat "C:\path\to\project" --venv "C:\path\to\.venv"
```

### Custom port

```bash
python start_mcp_qa.py "/path/to/project" --port 8015 --venv "/path/to/venv"
```

SSE URL:

```text
http://localhost:8015/sse/?token=YOUR_TOKEN
```

---

## Token Protection

Token priority:

1. `--token "your-fixed-token"`
2. `MCP_QA_TOKEN` environment variable
3. auto-generated temporary token

### Local-only use

For local-only use, auto-generated tokens are usually enough.

### Public tunnel use

For ChatGPT connection through ngrok or Cloudflare Tunnel, use a fixed token:

```bash
export MCP_QA_TOKEN="long-random-token"
python start_mcp_qa.py "/path/to/project" --token "$MCP_QA_TOKEN"
```

Public tunnel URL example:

```text
https://your-tunnel-domain.example/sse/?token=YOUR_TOKEN
```

Never publish the token in GitHub.

---

## Testing the Server

### Check root endpoint without token

Expected: `401 Unauthorized`

```bash
curl -i "http://localhost:8008/"
```

### Check root endpoint with token

Expected: `200 OK`

```bash
curl -i "http://localhost:8008/?token=$MCP_QA_TOKEN"
```

### List tools

```bash
curl -s -X POST "http://localhost:8008/sse/?token=$MCP_QA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 -m json.tool
```

You should see tools such as:

```text
search
fetch
write_file
create_directory
delete_file
shell
apply_patch
start_localhost
localhost_status
stop_localhost
capture_web_screenshot
capture_web_screenshot_batch
```

---

## Using With ChatGPT

ChatGPT can connect to remote MCP servers through ChatGPT Apps / Developer Mode. For local development, ChatGPT needs an HTTPS-accessible endpoint, so expose the local server through a secure tunnel.

### Important ChatGPT notes

- ChatGPT Apps were previously called custom connectors.
- Developer Mode provides fuller MCP tool access, including read and write tools.
- For ChatGPT connection, the local server must be reachable from ChatGPT over HTTPS.
- You can use ngrok, Cloudflare Tunnel, or another secure tunnel during development.
- Keep token protection enabled.

### Local development flow

1. Start the MCP server locally:

```bash
python start_mcp_qa.py "/path/to/project" --venv "/path/to/venv" --token "$MCP_QA_TOKEN"
```

2. Expose local port through a tunnel:

```bash
ngrok http 8008
```

3. Build the ChatGPT connector URL:

```text
https://YOUR-NGROK-DOMAIN/sse/?token=YOUR_TOKEN
```

4. In ChatGPT:

```text
Settings → Apps / Connectors → Advanced settings → Developer mode
```

5. Create a new app / connector using your public HTTPS MCP URL.

6. Start a new chat and select the app from the composer tools.

### Recommended ChatGPT prompt

```text
Use the MCP Localhost QA app only. Inspect the repository root, fetch the README and docs folders, and summarize the architecture. Do not modify any files.
```

### Write-action prompt

```text
Use the MCP Localhost QA app. Search for the broken link in docs/README.md. Fetch the file and propose a patch first. Do not write or apply any patch until I approve it.
```

---

## Using With OpenAI Codex

Codex is a local coding agent that can inspect, modify, and run code in the selected directory. MCP is useful when you want Codex to reuse the same structured server tools used by ChatGPT and other MCP clients, especially for localhost QA screenshots and evidence.

### Codex configuration file

User-level config usually lives at:

```text
~/.codex/config.toml
```

Project-level config may be placed in:

```text
.codex/config.toml
```

### Streamable HTTP configuration shape

Codex configuration supports MCP server entries under `mcp_servers`.

Example:

```toml
[mcp_servers.localhost_qa]
url = "http://localhost:8008/sse/?token=YOUR_TOKEN"
startup_timeout_sec = 10
tool_timeout_sec = 60
default_tools_approval_mode = "prompt"

# Optional safety allowlist
enabled_tools = [
  "search",
  "fetch",
  "localhost_status",
  "capture_web_screenshot",
  "capture_web_screenshot_batch"
]
```

### Safer read-only Codex profile

```toml
[mcp_servers.localhost_qa_readonly]
url = "http://localhost:8008/sse/?token=YOUR_TOKEN"
default_tools_approval_mode = "prompt"
enabled_tools = ["search", "fetch", "localhost_status", "capture_web_screenshot"]
disabled_tools = ["write_file", "delete_file", "apply_patch", "shell", "start_localhost", "stop_localhost"]
```

### Compatibility note

This v1.4 server exposes an HTTP/SSE endpoint at `/sse/`. Some MCP clients are moving toward the newer Streamable HTTP `/mcp` style. If a Codex version does not accept the SSE URL directly, use one of these options:

- add a Streamable HTTP endpoint to this server,
- use an MCP transport adapter,
- use ChatGPT Developer Mode for the SSE connection,
- keep Codex as the code executor and use ChatGPT/Claude/Gemini for MCP evidence review.

---

## Using With Claude / Claude Desktop / Claude Code

Claude has multiple MCP-capable surfaces. Configuration depends on whether you are using Claude Desktop, Claude Code, or the Claude API MCP connector.

### Claude Desktop direct URL style

If your Claude Desktop version supports URL-based remote MCP servers, configure:

```json
{
  "mcpServers": {
    "localhost-qa": {
      "url": "http://localhost:8008/sse/?token=YOUR_TOKEN"
    }
  }
}
```

Common config locations:

```text
macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
Windows: %APPDATA%\Claude\claude_desktop_config.json
```

After saving, fully quit and restart Claude Desktop.

### Claude Desktop through adapter

If direct URL/SSE is not supported in your installed Claude Desktop client, use a stdio adapter such as `mcp-remote`:

```json
{
  "mcpServers": {
    "localhost-qa": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8008/sse/?token=YOUR_TOKEN"
      ]
    }
  }
}
```

### Claude Code guidance

For Claude Code, prefer a checked-in or team-reviewed MCP configuration only after security review. Claude Code can run tools that affect source code, so enforce:

- trusted MCP server allowlist,
- per-tool permissions,
- human approval for write actions,
- read-only mode for architecture and BA review,
- no public tokens in config files.

Recommended prompt:

```text
Use the localhost QA MCP server in read-only mode. Review the route registry against the actual frontend routes. Report mismatches only. Do not edit files.
```

---

## Using With Cursor

Cursor supports MCP servers for giving its AI agent access to external tools and context.

### Project-level Cursor config

Create:

```text
.cursor/mcp.json
```

Example:

```json
{
  "mcpServers": {
    "localhost-qa": {
      "url": "http://localhost:8008/sse/?token=YOUR_TOKEN"
    }
  }
}
```

### Global Cursor config

Create or edit:

```text
~/.cursor/mcp.json
```

Example:

```json
{
  "mcpServers": {
    "localhost-qa": {
      "url": "http://localhost:8008/sse/?token=YOUR_TOKEN"
    }
  }
}
```

### Cursor workflow recommendation

Use Cursor for fast coding and local implementation. Use this MCP server when Cursor’s agent needs standardized access to:

- QA evidence folders,
- local screenshots,
- repeatable smoke tests,
- cross-client evidence shared with ChatGPT or Claude.

### Cursor safety recommendation

For team repos, treat `.cursor/mcp.json` like infrastructure code. Review changes carefully because MCP config can grant powerful tool access.

---

## Using With Gemini CLI

Gemini CLI supports MCP servers through `~/.gemini/settings.json`.

### Gemini SSE configuration

```json
{
  "mcpServers": {
    "localhost-qa": {
      "url": "http://localhost:8008/sse/?token=YOUR_TOKEN",
      "timeout": 30000,
      "trust": false
    }
  }
}
```

### Gemini allowed list

```json
{
  "mcp": {
    "allowed": ["localhost-qa"]
  },
  "mcpServers": {
    "localhost-qa": {
      "url": "http://localhost:8008/sse/?token=YOUR_TOKEN",
      "timeout": 30000,
      "trust": false
    }
  }
}
```

### Gemini prompt

```text
Use @localhost-qa to inspect the docs folder and summarize all QA evidence generated in the last milestone. Do not modify files.
```

### Compatibility note

Gemini CLI supports multiple transport types, including stdio, SSE, and Streamable HTTP. This server’s endpoint is SSE-style, so use the `url` field.

---

## Recommended Prompt Patterns

### Read-only repository review

```text
Use the MCP filesystem tools only. Search the repository for authentication, permissions, and payment-related files. Fetch only relevant files. Produce a PRD compliance report. Do not modify files.
```

### Architecture review

```text
Use the local filesystem MCP server to inspect docs/architecture, docs/ai-context, and registry files. Compare the implementation structure against the architecture documentation. Report gaps and risks. Do not modify files.
```

### QA smoke test

```text
Use Localhost QA tools. Start the app using the documented dev command, wait until the homepage is ready, capture screenshots for the homepage and dashboard, and save them under docs/qa/evidence/screenshots/stage-01/. Then write a Markdown QA report under docs/qa-evidence/stage-01-smoke/. Do not change source code.
```

### Patch with approval gate

```text
Search for the bug. Fetch the relevant file. Explain the minimal patch first. Do not call write_file or apply_patch until I explicitly approve.
```

### BA acceptance review

```text
Use filesystem tools to compare the acceptance criteria in docs/PRD against the implemented routes and UI surface registry. Produce a business-readable pass/fail table with evidence paths. Do not modify files.
```

---

## QA Evidence Workflow

### Recommended folder structure

```text
docs/qa-evidence/
└─ stage-01-smoke-test/
   ├─ 001-summary.md
   ├─ 002-route-check.md
   ├─ screenshots/
   │  ├─ dashboard.png
   │  └─ settings.png
   └─ logs/
      └─ dev-server.log
```

or use the server defaults:

```text
docs/qa/evidence/logs/
docs/qa/evidence/screenshots/
```

### Evidence naming convention

Use serial names for review clarity:

```text
001-localhost-start.md
002-homepage-screenshot.png
003-dashboard-screenshot.png
004-route-registry-review.md
005-final-qa-summary.md
```

### Minimum QA report template

```markdown
# QA Evidence Report

## Scope

## Environment

- OS:
- Project path:
- MCP server version:
- App command:
- Localhost URL:

## Steps Performed

1.
2.
3.

## Evidence

| Evidence | Path | Result |
|---|---|---|
| Homepage screenshot | docs/qa/evidence/screenshots/... | Passed |
| Server log | docs/qa/evidence/logs/... | Passed |

## Findings

## Risks

## Final Status

Passed / Passed with warnings / Failed
```

---

## Example Developer Workflows

### Laravel + Vite

```text
Start Laravel with `php artisan serve --host=127.0.0.1 --port=8000` from the repo root. Then capture screenshots of /login, /dashboard, and /settings. Save evidence under docs/qa/evidence/screenshots/stage-01/.
```

### React / Vite

```text
Run `npm run dev -- --host 127.0.0.1 --port 5173`, wait until http://localhost:5173 is ready, capture homepage and dashboard screenshots, and report console-visible rendering issues based on screenshot evidence.
```

### MkDocs / Docusaurus

```text
Start the documentation site locally, capture screenshots of the homepage, architecture page, developer guide page, and QA page. Save a docs review report under docs/qa-evidence/docs-site-smoke/.
```

### Regression check

```text
Compare current screenshots against the previous evidence folder. Report UI regressions, missing pages, navigation breaks, and broken layout issues. Do not modify files.
```

---

## Business Analyst and System Architect Workflows

### BA workflow

1. Fetch PRDs or requirements documents.
2. Extract acceptance criteria.
3. Search implementation files for matching routes, UI labels, jobs, events, policies, or workflows.
4. Produce a pass/fail matrix.
5. Save a review report under `docs/qa-evidence/<stage>/`.

Prompt:

```text
Use Local Filesystem tools to review PRD 08 against implemented files. Build a pass/fail matrix for every acceptance criterion. Include evidence file paths. Do not modify files.
```

### System architect workflow

1. Fetch architecture docs.
2. Fetch route, surface, permission, event, job, workflow, and AI contract registries.
3. Search source code for implementation alignment.
4. Identify architectural drift.
5. Recommend small, reviewable tasks.

Prompt:

```text
Act as system architect reviewer. Use the filesystem tools to compare architecture registry files with implementation. Report architectural drift, missing abstractions, hardcoded logic, and violations of the SaaS core boundary. Do not modify files.
```

---

## Extensions and Recommended Add-ons

This package is a strong v1.4 starter. For a polished GitHub developer release, add the following.

### 1. Streamable HTTP endpoint

Current server uses an HTTP/SSE-style endpoint at `/sse/`. Add a modern Streamable HTTP endpoint at:

```text
/mcp
```

This improves compatibility with newer MCP clients and protocol versions.

### 2. Read-only mode

Add startup flag:

```bash
--read-only
```

Disable:

```text
write_file
delete_file
apply_patch
shell
start_localhost
stop_localhost
```

Keep:

```text
search
fetch
localhost_status
capture_web_screenshot
```

### 3. Tool profile modes

Recommended profiles:

| Profile | Enabled Tools |
|---|---|
| `ba-review` | `search`, `fetch` |
| `architect-review` | `search`, `fetch`, `shell` read commands only |
| `qa-evidence` | `search`, `fetch`, `start_localhost`, `localhost_status`, `capture_web_screenshot`, `stop_localhost` |
| `developer-write` | all tools with approval |
| `admin` | all tools |

### 4. Audit log

Add append-only audit records:

```text
.mcp/audit/YYYY-MM-DD.jsonl
```

Each record should include:

```json
{
  "timestamp": "2026-06-25T00:00:00Z",
  "tool": "write_file",
  "arguments_hash": "...",
  "path": "docs/example.md",
  "result": "success"
}
```

### 5. Evidence report generator

Add a tool:

```text
generate_qa_report
```

It should summarize:

- process status,
- screenshots captured,
- logs created,
- failed routes,
- warnings,
- final pass/fail status.

### 6. Browser console and network capture

Extend screenshot tools to capture:

- console errors,
- failed network requests,
- page title,
- HTTP status,
- selected DOM text.

### 7. Git tools

Add safe read-only Git tools:

```text
git_status
git_diff
git_log
git_branch
git_show
```

Keep write Git operations disabled unless explicitly enabled.

### 8. Test runner presets

Add command presets:

```text
pytest
phpunit
npm test
npm run lint
npm run typecheck
composer test
```

### 9. Docker support

Add:

```text
Dockerfile
docker-compose.yml
```

Benefits:

- reproducible setup,
- easier developer onboarding,
- safer environment isolation.

### 10. MCP Inspector instructions

Add instructions for validating the server using MCP Inspector or equivalent client-debugging tools.

### 11. GitHub templates

Add:

```text
.github/ISSUE_TEMPLATE/bug_report.md
.github/ISSUE_TEMPLATE/feature_request.md
.github/pull_request_template.md
SECURITY.md
CODE_OF_CONDUCT.md
CONTRIBUTING.md
```

### 12. CI smoke tests

Add GitHub Actions to run:

- Python syntax check,
- unit tests for path validation,
- token auth tests,
- delete_file tests,
- no-secret scan,
- README link check.

---

## Troubleshooting

### Python not found

Windows:

```powershell
py --version
```

Linux/macOS:

```bash
python3 --version
```

### Playwright Chromium fails on Linux

Run starter with:

```bash
--with-deps
```

or manually:

```bash
python -m playwright install --with-deps chromium
```

### Token returns 401

Check that the URL includes:

```text
?token=YOUR_TOKEN
```

or use header:

```text
Authorization: Bearer YOUR_TOKEN
```

or:

```text
X-MCP-Token: YOUR_TOKEN
```

### Port already in use

Use another port:

```bash
python start_mcp_qa.py "/path/to/project" --port 8010
```

### Client does not show tools

Check:

- server is running,
- token is correct,
- URL path includes `/sse/`,
- client supports SSE or has an adapter,
- JSON config syntax is valid,
- project path exists,
- firewall is not blocking localhost,
- tunnel URL is HTTPS for ChatGPT.

### Screenshot timeout

Use:

```json
{
  "wait_until": "domcontentloaded",
  "wait_ms": 1500,
  "timeout_ms": 60000
}
```

### Delete file confusion

v1.4 accepts:

```text
path
id
file_id
target
paths[]
file:// URLs
/docs/... repo-root style paths
```

Use temporary folders for delete tests:

```text
docs/qa-evidence/mcp-smoke-test-v1-4/
```

---

## Known Limitations

1. **Current server transport is SSE-style**  
   Newer clients may prefer Streamable HTTP.

2. **No built-in HTTPS**  
   Use ngrok, Cloudflare Tunnel, or a reverse proxy for ChatGPT.

3. **No OAuth**  
   Token auth is simple and useful for local development but not enough for multi-user production deployments.

4. **No role-based authorization yet**  
   Tool-level profiles should be added before team-wide adoption.

5. **No binary file writing**  
   `write_file` is UTF-8 text oriented.

6. **Fetch size limit**  
   Large files are blocked to avoid oversized responses.

7. **Shell tool is powerful**  
   Even with workspace restriction, shell commands require careful review.

8. **Not a production public MCP gateway**  
   This is a local QA/developer tool.

---

## Production Hardening Roadmap

Before using this in a team or enterprise setting, add:

- Streamable HTTP `/mcp` endpoint.
- HTTPS termination.
- OAuth or mTLS for remote deployments.
- Role-based tool policies.
- Read-only mode.
- Per-tool approval defaults.
- Signed audit logs.
- Centralized config policy.
- Docker image.
- CI smoke tests.
- Security scanning.
- Versioned API/tool schema docs.
- Clear data handling policy.
- Tool allowlist / denylist.
- Rate limits.
- Request size limits.
- Log redaction.

---

## Recommended GitHub Files

### `README.md`

Main documentation and quickstart.

### `SECURITY.md`

Explain:

- local-only security expectations,
- token rules,
- public tunnel warning,
- responsible disclosure process.

### `CONTRIBUTING.md`

Explain:

- coding style,
- test requirements,
- safe path validation rules,
- tool schema update policy.

### `CHANGELOG.md`

Track versions:

```markdown
## v1.4
- Hardened delete_file input shapes.
- Added token preservation in systemd example.

## v1.3
- Improved apply_patch support.
- Added screenshot wait_until option.
```

### `.env.example`

```env
MCP_QA_HOST=localhost
MCP_QA_PORT=8008
MCP_QA_TOKEN=replace-with-long-random-token
```

### `LICENSE`

Recommended options:

- MIT for maximum adoption,
- Apache-2.0 if you want patent language,
- GPL only if you require derivative openness.

For developer tools, MIT or Apache-2.0 is usually easiest.

---

## Glossary

| Term | Meaning |
|---|---|
| MCP | Model Context Protocol. |
| MCP server | Tool/data provider connected to AI clients. |
| MCP host | App such as ChatGPT, Claude, Cursor, Gemini CLI, Codex. |
| Tool | Callable function exposed by MCP server. |
| SSE | Server-Sent Events, used by this v1.4 server endpoint. |
| Streamable HTTP | Newer MCP HTTP transport using a single endpoint. |
| Localhost | Local web server on the same machine. |
| QA evidence | Screenshots, logs, reports, and verification artifacts. |
| venv | Python virtual environment. |
| Token | Secret value required to access this MCP server. |

---

## References

- Model Context Protocol introduction: https://modelcontextprotocol.io/docs/getting-started/intro
- MCP transport specification: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- MCP tools specification: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- ChatGPT Apps / MCP server documentation: https://developers.openai.com/api/docs/mcp
- ChatGPT Developer Mode: https://developers.openai.com/api/docs/guides/developer-mode
- ChatGPT Apps connection guide: https://developers.openai.com/apps-sdk/deploy/connect-chatgpt
- OpenAI Codex CLI: https://developers.openai.com/codex/cli
- OpenAI Codex configuration reference: https://developers.openai.com/codex/config-reference
- Cursor MCP documentation: https://cursor.com/docs/mcp
- Gemini CLI MCP server documentation: https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html
- Anthropic MCP announcement: https://www.anthropic.com/news/model-context-protocol

---

## Maintainer Notes

Recommended next release target: **v1.5**

Priority changes:

1. Add Streamable HTTP `/mcp` endpoint.
2. Add `--read-only` flag.
3. Add tool profiles.
4. Add audit log.
5. Add GitHub-ready tests.
6. Add Dockerfile.
7. Add security policy and contribution guide.

