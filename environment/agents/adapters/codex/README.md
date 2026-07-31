<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/codex/README.md
layer: adapter
owner: governance-control-plane
status: planned
version: 1.0.0
updated: 2026-07-28
/L9_META -->

# Codex Adapter — L9 governance node on OpenAI Codex (cloud + CLI)

Registry identity: `agents.codex` (`agent_id=codex`, `user_id=codex_agent`,
role `implementer`, status **planned** — flip to `active` in the registry
when the token is issued).

| Need | Carrier |
|---|---|
| Skill discovery | git-tracked `AGENTS.md` in each governed repo (Codex reads it natively) |
| Boot context | `AGENTS.md` block below + repo docs |
| Shared memory | MCP config (`mcp.template.json` here) — Codex CLI `~/.codex/config.toml` `[mcp_servers]`, or cloud environment settings |
| GitHub | Codex's native GitHub connector |

## Setup

1. Prerequisite: routable memory endpoint (`docs/MEMORY_TOPOLOGY.md` Option A).
2. Issue `L9_MEMORY_TOKEN__CODEX` (≥24 chars), add `"codex": "<token>"` to
   `agent_tokens.local.json`, re-render principals, restart the server.
3. CLI: add to `~/.codex/config.toml`:

```toml
[mcp_servers.l9-memory]
url = "https://<memory-host>/mcp"
http_headers = { "Authorization" = "Bearer <L9_MEMORY_TOKEN__CODEX>" }
```

   Cloud: set the same URL/header in the Codex environment's MCP settings and
   env vars from `environment.env.example`.
4. Append `agents-block.md` content to the `AGENTS.md` of each governed repo
   Codex works in (one PR; the block is identical everywhere).

## Role limits (implementer)

Code implementation and PR remediation in `assigned_groups` only. Must claim
before starting (WORK_CLAIM_PROTOCOL.md); no promotion; writes with
`user_id=codex_agent`, `source=codex` only.
