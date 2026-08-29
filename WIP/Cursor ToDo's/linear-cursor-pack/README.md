# Linear -> Cursor Integration Pack

Runbook-driven setup for connecting Linear to Cursor in the
`Quantum-L9/Cursor-Governance` repository.

Covers two independent integration paths:

- **Path A - Linear MCP** (IDE-side, read/write issues from Cursor Agent)
- **Path B - Cursor Cloud Agent for Linear** (delegate issues to `@Cursor`)

Path A is the default. Path B is opt-in and gated behind CI hardening,
because cloud agents run outside your local hooks.

## Contents

| File | Purpose |
|---|---|
| `RUNBOOK.md` | RB-LIN-001. The operator document. Start here for manual runs. |
| `START-HERE-PROMPT.md` | Copy-paste prompt for Cursor Agent. |
| `AGENT_TASK.md` | Machine-executable task spec Cursor follows. |
| `CHECKLIST.md` | Sign-off checklist for auditability. |
| `templates/mcp.linear.json` | The MCP server block to merge into `.cursor/mcp.json`. |
| `templates/env.linear.example` | Optional PAT contract for the fallback transport. |
| `.cursor/rules/linear-workflow.mdc` | Always-apply rule teaching the agent your issue conventions. |
| `scripts/verify-linear-mcp.sh` | Post-setup validation. |
| `scripts/verify-linear-mcp.ps1` | Windows equivalent. |

## Quick start

1. Unzip at the repo root of `Cursor-Governance`.
2. Read `RUNBOOK.md` Section 3 (preconditions).
3. Paste `START-HERE-PROMPT.md` into Cursor Agent, or follow Section 4.2 manually.
4. Run `./scripts/verify-linear-mcp.sh`.
