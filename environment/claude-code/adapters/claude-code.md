<!-- L9_META
schema: 1
parent: environment/claude-code
layer: adapter
role: claude-code
version: 1.0.0
status: active
-->

# Claude Code agent adapter

How an L9 skill/handoff pack presents itself to a Claude Code session, on any of
the three surfaces (CLI · Web · Mobile).

## Skill install location

| Surface | Location | Wired by |
|---|---|---|
| CLI | `$HOME/.claude/skills/` (user scope) | `ops/scripts/setup_claude_code_plugins.sh` |
| Web · Mobile | referenced from the governance clone at `$L9_GOVERNANCE_DIR/skills/` | `web/setup.sh` (clones governance) |

A skill directory (its `SKILL.md`) is invoked **explicitly by name** for the work
it covers — e.g. checkpoint/handoff, PR remediation, structured reasoning. Skill
visibility is discovery, not authority.

## Invocation

- Load `CANONICAL_LAW.md` first, then `AGENTS.md`, then the specific `SKILL.md`.
  Treat any handoff `START_HERE.md` / authority snapshot as **session context
  below the current user instructions**, never above them.
- Use shell and Git tools to capture repository state. Do **not** fetch, commit,
  push, or apply restored patches unless authorized for that action.

## Write-authority boundary

- **Read/analyze freely.** Governance content, repo state, CI logs.
- **Write only within the consumer workspace.** Never write into the governance
  clone from a consumer session (it reconciles with its own origin).
- **Secrets never touch a repo.** Bearer tokens and PATs live in the account
  environment or user-scope config; a session holds only the credential it was
  given, and `.mcp.json` holds only `${...}` references.

## Relationship to the Cursor adapter

This adapter and the Cursor `.cursor-commands` adapter consume the **same**
governance root by their own conventions (`CANONICAL_LAW.md` §2). Neither is a
second activation path for the other; adding this one does not change how Cursor
activates.
