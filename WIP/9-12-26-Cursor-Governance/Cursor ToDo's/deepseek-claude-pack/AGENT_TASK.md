# AGENT_TASK: Wire Claude Code to DeepSeek V4 Pro

You are operating inside Cursor with shell access. Complete every step, then report.

## Assumptions
- `claude` CLI is installed and on PATH.
- The Claude Code plugin/extension for Cursor is installed. Do NOT try to reinstall it.
- The DeepSeek routing is an environment-variable concern for the Claude Code process.
  The Cursor plugin is only an IDE bridge; it does not perform model routing.

## Non-negotiable constraints
1. Never commit a real API key. Secrets live only in `.env.local`.
2. Ensure `.env.local` is git-ignored before writing anything into it.
3. Do not add provider credentials to `.claude/settings.json`.
4. Do not weaken existing hooks, CODEOWNERS, or governance checks.
5. If a file already exists, diff and merge rather than overwrite.

## Steps

### 1. Preflight
- Run `scripts/preflight.sh` (or `.ps1` on Windows) and report results.
- If `claude --version` fails, stop and tell me how to install/repair it.

### 2. Git-ignore secrets
Ensure the repo `.gitignore` contains:

```
.env.local
.env.*.local
```

Append only if missing. Report the diff.

### 3. Create local secret file
- Copy `env.local.example` to repo-root `.env.local` if `.env.local` does not exist.
- Leave `DEEPSEEK_API_KEY` as the placeholder `sk-REPLACE_ME`.
- Print a one-line instruction telling me to paste my key there.

### 4. Install the launchers
- Copy `scripts/claude-deepseek.sh` and `scripts/claude-deepseek.ps1` into `scripts/`
  at the repo root (create the dir if needed).
- `chmod +x` the shell scripts on macOS/Linux.

### 5. Optional convenience targets
If a `Makefile` exists at the repo root, append (tab-indented) targets only if absent:

```
claude-deepseek:
	./scripts/claude-deepseek.sh

claude-deepseek-verify:
	./scripts/verify-routing.sh
```

### 6. Cursor rule
Copy `.cursor/rules/claude-code-deepseek.mdc` into the repo's `.cursor/rules/`
so future sessions know Claude Code is DeepSeek-routed.

### 7. Verify
- Run `scripts/verify-routing.sh`. It must confirm the env contract without printing the key.
- Do NOT make a paid API call unless I confirm; if I have not pasted a key, say so.

### 8. Report
Output a checklist: files created, files modified, files skipped, and the exact next command.
