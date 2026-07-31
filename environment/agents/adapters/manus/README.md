<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/manus/README.md
layer: adapter
owner: governance-control-plane
status: active
version: 1.1.0
updated: 2026-07-31
/L9_META -->

# Manus Adapter — L9 governance node on Manus cloud

Registry identity: `agents.manus` in `../../agent_registry.yaml`
(`agent_id=manus`, `user_id=manus_agent`, role `researcher-builder`, **active**).

Contract: `../ADAPTER_CONTRACT.md` (same three carriers as Claude Code).
Claude Code itself remains at `environment/claude-code/` — this adapter does
not replace it.

| Need | Claude Code carrier | Manus carrier |
|---|---|---|
| Skill discovery | git-tracked `.claude/` | **Manus Skills** (account-registered) |
| Boot context | SessionStart hook | `session_bootstrap.md` → project instructions / skill |
| Shared memory | account env + `.mcp.json` | `mcp-connector.json` + `environment.env.example` |
| Network | `web/network-policy.md` | `docs/network-allowlist.md` |
| GitHub | `GH_TOKEN` account env | GitHub integration (already authenticated) |

## Setup

Follow **`setup.md`** (step-by-step). Short form:

1. Memory: `https://memory.quantumaipartners.com` (live Option A).
2. Issue/sync manus token via `docs/DEPLOY.md`.
3. Create Custom MCP connector from `mcp-connector.json`.
4. Paste `environment.env.example` + `session_bootstrap.md`.

## Session behavior

On any task touching a governed repo, Manus must: resolve `group_id` from
`ops/graphiti/group_registry.yaml` (never `main`/`default`); search memory for
context AND open `task-claim` episodes; claim before starting per
`docs/WORK_CLAIM_PROTOCOL.md`; write episodes with its own identity
(`user_id=manus_agent`, `source=manus`); mark claims `done`/`released` when
stopping. Role limits: research, analysis, cross-repo builds, docs; it does
not promote memories and does not claim orchestrator/implementer work unless
delegated via an `assigned_to: manus` claim.
