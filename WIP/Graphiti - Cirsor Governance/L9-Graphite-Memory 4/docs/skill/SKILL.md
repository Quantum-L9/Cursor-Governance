---
name: l9-graphiti-memory
description: Graphiti VPS memory — prefetch, group resolution, T0 memory-bank, episode writes, GMP Phase 0 MEMORY_PREFETCH. Use when wiring memory, debugging prefetch, bootstrap, or Graphiti health.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, graphiti, memory, prefetch, gmp]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-06-07
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
