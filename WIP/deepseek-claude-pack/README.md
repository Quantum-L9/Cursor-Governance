# DeepSeek V4 Pro -> Claude Code pack (Cursor-ready)

Drop this folder into your repo root (e.g. your `Cursor-Governance` checkout), open
`START-HERE-PROMPT.md`, and paste the single prompt into Cursor Agent.

Contents:

- `START-HERE-PROMPT.md` - the one prompt to paste into Cursor
- `AGENT_TASK.md` - the full instruction set Cursor executes
- `env.local.example` - env contract; copy to `.env.local` (git-ignored)
- `scripts/claude-deepseek.sh` / `.ps1` - launchers that route Claude Code to DeepSeek
- `scripts/preflight.sh` / `.ps1` - environment checks
- `scripts/verify-routing.sh` - asserts routing + secret hygiene
- `.cursor/rules/claude-code-deepseek.mdc` - persistent repo rule
- `docs/MOBILE.md`, `docs/TROUBLESHOOTING.md`
- `docs/MERGE-RUNBOOK.md` - for the agent merging PR #121

Assumes the Claude Code CLI and the Cursor Claude Code plugin are already installed.
The plugin is an IDE bridge only; routing is env-var based.
