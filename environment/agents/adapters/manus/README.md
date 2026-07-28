<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/manus/README.md
layer: adapter
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-28
/L9_META -->

# Manus Adapter — L9 governance node on Manus cloud

Registry identity: `agents.manus` in `../../agent_registry.yaml`
(`agent_id=manus`, `user_id=manus_agent`, role `researcher-builder`).

Manus sandboxes are ephemeral per task, but Manus has three persistent
carriers that map onto the claude-code adapter's pattern:

| Need | Claude Code carrier | Manus carrier |
|---|---|---|
| Skill discovery | git-tracked `.claude/` | **Manus Skills** (account-registered; the L9 skills already exist there) |
| Boot context | SessionStart hook | **Project instructions / skill preamble** (`session_bootstrap.md`) |
| Shared memory | account env + `.mcp.json` | **Custom MCP connector** (`mcp-connector.json`) with per-agent bearer token |
| GitHub | `GH_TOKEN` account env | GitHub integration (already authenticated) |

## Setup (one-time, ~5 minutes)

1. **Memory endpoint** — requires the routable HTTPS endpoint from
   `docs/MEMORY_TOPOLOGY.md` Option A. Loopback/tunnel deployments are
   unreachable from Manus sandboxes; this is a hard prerequisite.
2. **Issue the token** — generate a ≥24-char token for Manus, add it to
   `agent_tokens.local.json` on the render host as `"manus": "<token>"`,
   re-run `tools/render_principals.py`, restart the memory server.
3. **Create the connector** — in Manus, add a Custom MCP connector using
   `mcp-connector.json` as the template: URL
   `https://<memory-host>/mcp`, header `Authorization: Bearer <manus token>`.
4. **Install the bootstrap** — paste `environment.env.example` values into the
   connector/env configuration and add `session_bootstrap.md` content to the
   project instructions (or a Manus skill) so every Manus session boots with
   L9 identity + the work-claim rule.

## Session behavior (what the bootstrap enforces)

On any task touching a governed repo, Manus must: resolve `group_id` from
`ops/graphiti/group_registry.yaml` (never `main`/`default`); search memory for
context AND open `task-claim` episodes; claim before starting per
`docs/WORK_CLAIM_PROTOCOL.md`; write episodes with its own identity
(`user_id=manus_agent`, `source=manus`); mark claims `done`/`released` when
stopping. Role limits: research, analysis, cross-repo builds, docs; it does
not promote memories and does not claim orchestrator/implementer work unless
delegated via an `assigned_to: manus` claim.
