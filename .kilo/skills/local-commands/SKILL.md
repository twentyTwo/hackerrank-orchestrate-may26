---
name: local-commands
description: Run Git, Bash, PowerShell, and other shell commands quickly using local or any configured LLM
---

# Local Commands Skill

## Purpose

Provide a quick workflow for running common shell commands (Git, Bash, PowerShell, Python scripts, etc.) from within Kilo using the configured model, including local LLMs.

## When to Use

- The user wants to run a simple Git, Bash, PowerShell, or other shell command.
- The user wants to inspect repo status, logs, diffs, branches, or remotes.
- The user wants to execute a build, test, lint, or deploy command.
- The user wants to run a one-off script or utility.

## Workflow

1. Parse the user's request to determine the command to run.
2. If the request is ambiguous, ask the user to clarify the exact command.
3. Run the command using the Bash tool.
   - On Windows, PowerShell (`pwsh`) is the default shell.
   - Quote paths containing spaces.
   - Use the `workdir` parameter instead of `cd <dir> && <cmd>` patterns.
4. Return the output to the user.
5. If the command fails, surface the error and suggest a fix.

## Guidelines

- Prefer running single, focused commands.
- For destructive operations (e.g., `git reset --hard`, `rm -rf`), confirm with the user first.
- Do not commit changes unless the user explicitly asks.
- Do not push to remote unless the user explicitly asks.
- Redact any secrets or API keys from output before displaying.

## Common Commands Reference

| Task              | Command Example                    |
| ----------------- | ---------------------------------- |
| Repo status       | `git status`                       |
| Recent commits    | `git log --oneline -10`            |
| Current branch    | `git branch --show-current`        |
| Diff staged       | `git diff --cached`                |
| List files        | `ls` or `Get-ChildItem`            |
| Run tests         | `npm test` / `pytest` / etc.       |
| Install deps      | `npm install` / `pip install`      |
| Build project     | `npm run build` / appropriate cmd  |
