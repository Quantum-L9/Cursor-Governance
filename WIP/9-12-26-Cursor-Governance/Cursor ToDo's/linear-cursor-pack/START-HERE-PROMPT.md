# Copy-paste prompt for Cursor Agent

Paste this verbatim into Cursor Agent (Agent mode) with the repo open.

---

```
Read ./linear-cursor-pack/AGENT_TASK.md and execute it end to end.

Context you may assume:
- Cursor and the Claude Code plugin are already installed.
- I want Path A only for now: Linear MCP via the official remote server at
  https://mcp.linear.app/mcp using OAuth. Do NOT set up Path B (cloud agent
  delegation) and do not enable usage-based pricing.
- Never write a Linear API key into any tracked file. OAuth is preferred and
  needs no secret at all.
- Target repo: Quantum-L9/Cursor-Governance.
- Do NOT modify CANONICAL_LAW.md, ORG_INVARIANTS.yaml, CODEOWNERS,
  .claude/settings.json, or anything under .claude/hooks/.
- Linear is the work queue and audit record. It is NOT a memory store; that
  role belongs to l9-graphiti-memory. Do not build any memory-like sync.

Follow RUNBOOK.md Section 4.2 for execution and Section 5 for validation.
Work autonomously. Then report a checklist of exactly what you changed, plus
the one command I run next and the one manual step only I can do.
```

---

After the agent finishes, the manual step it cannot do for you is the OAuth
click-through: Cursor Settings > Tools & MCP > Linear > **Needs login**.
