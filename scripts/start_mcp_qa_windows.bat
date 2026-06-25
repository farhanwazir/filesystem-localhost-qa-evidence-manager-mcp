@echo off
setlocal
REM Starts the MCP Localhost QA starter. Pass your project path as the first argument.
REM Example: start_mcp_qa_windows.bat "C:\path\to\project" --venv "C:\path\to\venv"
python "%~dp0start_mcp_qa.py" %*
