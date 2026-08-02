<!-- L9_META
l9_schema: 1
parent: l9-graphiti-memory
origin: memory-playbook-v2
tags: [graphiti, memory, identity, buckets]
status: active
version: 2.0.0
updated: 2026-08-02
/L9_META -->

# Identity and buckets

Thin pointer file. **SSOT registries and topology live elsewhere** — Load them; do not fork.

| Concern | SSOT | Meaning |
|---------|------|---------|
| **What** repo memory is about | `ops/graphiti/group_registry.yaml` | Shared `group_id` (e.g. `cursor-governance`) |
| **Who** is writing | `environment/agents/agent_registry.yaml` | `agent_id`, `user_id`, `role`, `source`, token env |
| **Planes** | `environment/agents/docs/MEMORY_TOPOLOGY.md` | Cursor tunnel `:8100` vs HTTPS `memory.quantumaipartners.com` |
| **Resolution code** | `ops/graphiti/group_resolver.py` | Repo slug from remote/path; **no agent_id in group_id** |

## Hard law

| Action | Bucket | Notes |
|--------|--------|-------|
| **Write** | Resolved **repo** `group_id` only | CLI blocks `workspace_group` (`igor-workspace`) |
| **Read** | `[repo_group, igor-workspace]` when repo ≠ workspace | Prefetch may mention workspace — that is **read fan-in**, not write |
| **Forbidden write** | `main`, `default`, `""`, `test`, bare workspace via `cmd_write` | Rule 98 |

## Cursor surface (default this IDE)

| Field | Value (from registries) |
|-------|-------------------------|
| `agent_id` | `cursor` |
| `user_id` | `cursor_agent` |
| `role` | `orchestrator` |
| `source` | `cursor` |
| Token | `GRAPHITI_MCP_TOKEN` (legacy) / `L9_MEMORY_TOKEN__CURSOR` |
| Default transport | `graphiti_memory_client.py` → tunnel `127.0.0.1:8100` |

## Control plane surface (when `l9-memory` available)

Bearer → `MemoryPrincipal` (server-derived). Namespace grants by **role**. Same `group_id` law. Operating sequence: upstream https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/skill/SKILL.md

## Bind checklist (every write)

```bash
python3 ops/graphiti/graphiti_memory_client.py resolve
# expect: group_id=<repo>, readonly=false, method=registry
# NEVER invent group_id; NEVER use agent_id as group_id
```
