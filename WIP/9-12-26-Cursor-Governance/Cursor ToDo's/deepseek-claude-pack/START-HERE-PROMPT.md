# Paste this into Cursor Agent (single prompt)

Copy everything inside the block below into Cursor's Agent chat with this pack's folder
open (or after dropping the pack into your repo root). Then press enter once.

---

```
Read ./deepseek-claude-pack/AGENT_TASK.md and execute it end to end.

Context you may assume:
- The Claude Code CLI and the Claude Code plugin/extension for Cursor are already installed.
- I want Claude Code (not Cursor Agent) routed to DeepSeek V4 Pro via DeepSeek's
  Anthropic-compatible endpoint.
- Never write my real API key into any tracked file. Only .env.local (git-ignored).
- Target repo: Quantum-L9/Cursor-Governance. Do not modify .claude/settings.json
  permissions, hooks, or governance files except where AGENT_TASK.md explicitly allows.

Work autonomously. Report a checklist of what you changed and the exact command I run next.
```
---

## Then run

macOS/Linux:

    ./scripts/claude-deepseek.sh

Windows PowerShell:

    ./scripts/claude-deepseek.ps1
