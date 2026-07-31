<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/gemini/README.md
layer: adapter
owner: governance-control-plane
status: planned
version: 1.0.0
updated: 2026-07-28
/L9_META -->

# Gemini Adapter — L9 reviewer node on Gemini CLI

Registry identity: `agents.gemini` (`agent_id=gemini`, `user_id=gemini_agent`,
role `reviewer`, status **planned**). As a reviewer, Gemini writes ONLY into
`<group>.reviews` namespaces of its assigned repos — the server rejects
anything else once principals are rendered.

| Need | Carrier |
|---|---|
| Skill discovery | git-tracked `GEMINI.md` / context files in governed repos |
| Boot context | `gemini-block.md` content in `GEMINI.md` |
| Shared memory | `settings.template.json` merged into `~/.gemini/settings.json` (`mcpServers` supports `httpUrl` + `headers` with `$VAR` expansion) |

## Setup

1. Prerequisite: routable memory endpoint (`docs/MEMORY_TOPOLOGY.md` Option A).
2. Issue `L9_MEMORY_TOKEN__GEMINI`, add `"gemini": "<token>"` to
   `agent_tokens.local.json`, re-render principals, restart server.
3. Export the env vars from `environment.env.example` in the shell profile
   that launches Gemini CLI, then merge `settings.template.json` into
   `~/.gemini/settings.json`.
4. Add `gemini-block.md` content to `GEMINI.md` in governed repos.
5. Flip `agents.gemini.status` to `active` in the registry and re-validate.

## Role limits (reviewer)

Review episodes only (`<group>.reviews`): PR findings, CI triage, quality
audits. No implementation claims, no promotion, no writes outside review
namespaces. Claims follow WORK_CLAIM_PROTOCOL.md with task titles prefixed
`review:`.
