---
name: l9-graphiti-memory
description: Graphiti VPS memory — prefetch, group resolution, T0 memory-bank, episode writes, GMP Phase 0 MEMORY_PREFETCH. Use when wiring memory, debugging prefetch, bootstrap, or Graphiti health.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, graphiti, memory, prefetch, gmp]
owner: igor_beylin
status: active
version: 1.2.0
updated: 2026-08-01
disable-model-invocation: false
---

# Graphiti Global Memory

## Purpose

Operate the Graphiti VPS memory layer (T1/T2) with local **memory-bank/** (T0) as resume SSOT. C1 MCP is **read-only legacy**.

## Feature flags

| Env | Default | Meaning |
|-----|---------|---------|
| `GRAPHITI_MEMORY_ENABLED` | `0` | Master switch for prefetch + writes |
| `GRAPHITI_WRITE_GATES` | `0` | Fail-closed edit/shell/subagent gates (GATES-002) |

Config: `~/.cursor/graphiti.env` (copy from `ops/graphiti/graphiti.env.example`).

## CLI (always from repo root)

```bash
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py resolve
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py search "query" --limit 5
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py conflicts
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py phase-lock
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py inject "current task"
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py write --body "..." --kind lesson
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py bootstrap --dry-run
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py stats
```

## Direct HTTP MCP tool contract (l9-shared-memory)

Claude Code (Web · Mobile · CLI) reaches the memory service through the
`l9-shared-memory` **HTTP MCP server** (`${L9_MEMORY_HTTP_URL}/mcp`, wired by
`.mcp.json`), **not** the `graphiti_memory_client.py` CLI above — that CLI is the
Cursor/legacy path. Server identifies as `l9-graphite-memory` (canonical SQLite
store + Graphiti semantic projection). When invoking MCP tools directly:

- **Identity is server-derived from the bearer token** → `agent_id=claude-code`.
  `L9_MEMORY_AGENT_ID` / `L9_MEMORY_SOURCE` document it; they are **not** call
  arguments. Never pass an `agent_id`/principal argument — the token is the only
  identity lever. Wrong token ⇒ wrong principal.
- **`memory.search` / `memory.hydrate` require `namespaces` — an ARRAY of strings**
  (not a singular `namespace`). A wildcard-only read grant **rejects a bare query**
  with `AuthorizationError` (code `-32010`): *"explicit namespace is required when
  read grants contain only wildcards."* Always name at least one namespace, e.g.
  `["cursor-governance"]` or `["l9-graphiti-memory"]`.
- **Writes** go through `memory.ingest` (alias `write`). **Health** through
  `memory.health` (reports canonical store, Graphiti projection circuit, outbox).
- Canonical tools are the `memory.*` names; bare aliases (`search`, `write`,
  `health`, `conflicts`, …) exist for compatibility.

Minimal authorized search call:

```json
{"name": "memory.search", "arguments": {"query": "governance", "namespaces": ["cursor-governance"], "limit": 5}}
```

## Session lifecycle

1. **sessionStart** — `session_start_memory_orchestrator.sh` runs code-graph health + Graphiti prefetch (when enabled).
2. **Resume** — read `memory-bank/activeContext.md` first; then cite prefetch episode names from `.cursor/graphiti-state/`.
3. **sessionEnd** — `graphiti-session-end.sh` writes T0 distill to memory-bank only (no T1 unless `/end-session`).

## GMP Phase 0

Run `conflicts` then `phase-lock` before GMP file edits when gates on:

```bash
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py conflicts
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py phase-lock
```

## GATES-002 activation

See `ops/graphiti/GATES-002-ACTIVATION.md`. Flip `GRAPHITI_WRITE_GATES=1` only after soak checklist passes.

## Wiring verify

```bash
bash .cursor-commands/ops/scripts/check_governance_wiring.sh "$(pwd)"
bash .cursor-commands/ops/graphiti/test_gate_e2e_full.sh
```

## Authority

1. `rules/03-graphiti-memory.mdc`
2. `ops/graphiti/MEMORY_BANK_POLICY.md`
3. `ops/graphiti/group_registry.yaml`
4. `rules/97-graph-layer-boundary.mdc`, `98-graphiti-memory-gate.mdc`, `99-graphiti-temporal.mdc`

## VPS deploy (human gate)

See `ops/graphiti/DEPLOY.md` (C1 `46.62.243.82`, SSH tunnel). Health/bootstrap require `OPENAI_API_KEY` on VPS + running `docker compose up`.
