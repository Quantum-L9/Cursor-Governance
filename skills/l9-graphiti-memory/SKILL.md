---
name: l9-graphiti-memory
description: Graphiti / L9 memory playbook — resolve correct buckets, read before Task/explore and exploratory repo research, write durable facts to the repo group. Wrap Quantum-L9/l9-graphiti-memory + ops/graphiti; do not rebuild MemoryService.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, graphiti, memory, prefetch, gmp, playbook]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-08-02
disable-model-invocation: false
---

# Graphiti Memory Playbook

## Purpose

Operate episodic memory correctly: **bind the bucket**, **read at the right time**, **write to the repo group**. Wrap what already exists — [Quantum-L9/l9-graphiti-memory](https://github.com/Quantum-L9/l9-graphiti-memory) and `ops/graphiti/` — do **not** reimplement MemoryService, admission, projections, or ADR catalogs.

Local T0 resume SSOT: **`memory-bank/`**.

## Compact workflow

1. **Bind** — `resolve`; record `group_id` / `readonly` / method. Load [identity-and-buckets.md](references/identity-and-buckets.md) (agent_id ≠ group_id).
2. **Load fixtures** — [authority-bindings.md](references/authority-bindings.md) (always + conditional). Prefer upstream skill + `l9-memory` when on PATH; else Cursor client.
3. **Read on schedule** — [read-write-timing.md](references/read-write-timing.md). **MUST** search/inject **before** Task/explore subagent and **before** exploratory repo digs.
4. **Act** — Grep/code-graph for gaps; cite memory hits in subagent prompts.
5. **Write** — proactive atomic T2 to **repo** group via CLI (`search` then `write`). Never `igor-workspace` / `main` / `default`.
6. **GMP Phase 0** — `conflicts` (+ `phase-lock` when gates on) before governed mutate.

## Dual surface (do not conflate)

| Plane | When | CLI |
|-------|------|-----|
| **Cursor IDE (default)** | Tunnel `:8100` | `python3 ops/graphiti/graphiti_memory_client.py …` |
| **Control plane** | `l9-memory` installed / HTTPS agents | `l9-memory …` per upstream skill |

Topology SSOT: `environment/agents/docs/MEMORY_TOPOLOGY.md`.

## Cursor CLI (from repo root)

```bash
python3 ops/graphiti/graphiti_memory_client.py health
python3 ops/graphiti/graphiti_memory_client.py resolve
python3 ops/graphiti/graphiti_memory_client.py search "query" --limit 5
python3 ops/graphiti/graphiti_memory_client.py inject "current task"
python3 ops/graphiti/graphiti_memory_client.py conflicts
python3 ops/graphiti/graphiti_memory_client.py phase-lock
python3 ops/graphiti/graphiti_memory_client.py write --kind lesson "durable fact…"
python3 ops/graphiti/graphiti_memory_client.py bootstrap --dry-run
python3 ops/graphiti/graphiti_memory_client.py stats
```

Prefer this CLI over raw MCP `add_memory` (resolves + blocks workspace-group writes).

## Pre-Task / pre-explore (non-negotiable)

```text
resolve → search|inject "<task>" → cite hits → only then Task/explore or exploratory Grep
```

If memory already answers, **do not** launch a blind research subagent.

## Feature flags

| Env | Default | Meaning |
|-----|---------|---------|
| `GRAPHITI_MEMORY_ENABLED` | `0` in example; session hooks may enable | Prefetch master switch |
| `GRAPHITI_WRITE_GATES` | `0` | Hook fail-closed; skill timing still mandatory |

Config: `~/.cursor/graphiti.env` (from `ops/graphiti/graphiti.env.example`).

## Proactive writes (T2)

When durable doctrine, lesson, or ADR delta lands:

```bash
python3 ops/graphiti/graphiti_memory_client.py resolve   # expect repo group, e.g. cursor-governance
python3 ops/graphiti/graphiti_memory_client.py search "topic" --limit 5
python3 ops/graphiti/graphiti_memory_client.py write --kind lesson "one atomic fact…"
```

Atomic format: rule `87-cursor-memory-kernel.mdc`.

## Resource map

- [references/authority-bindings.md](references/authority-bindings.md) — Load map SSOT
- [references/identity-and-buckets.md](references/identity-and-buckets.md) — group / agent / plane
- [references/read-write-timing.md](references/read-write-timing.md) — when to read/write
- Upstream skill: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/skill/SKILL.md
- Registries: `ops/graphiti/group_registry.yaml`, `environment/agents/agent_registry.yaml`
- Rules: `03`, `87`, `97`, `98`, `99` graphiti/memory

## Wiring verify

```bash
bash ops/scripts/check_governance_wiring.sh "$(pwd)"
python3 ops/graphiti/graphiti_memory_client.py health
```

## VPS / deploy (human gate)

See `ops/graphiti/DEPLOY.md` and `environment/agents/docs/DEPLOY.md`. Do not mutate C1 without explicit approval.
