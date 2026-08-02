<!-- L9_META
l9_schema: 1
parent: l9-graphiti-memory
origin: memory-playbook-v2
tags: [graphiti, memory, bindings, fixtures]
status: active
version: 2.0.0
updated: 2026-08-02
/L9_META -->

# Memory playbook — authority bindings

Load map for skill `l9-graphiti-memory`. **Wrap/call** permanent fixtures. **MUST NOT** paste upstream ADRs, harvest catalogs, or MemoryService internals into this skill pack.

**Repo doctrine:** `rules/46-wrap-call-existing-authority.mdc`.

Agents **MUST** `resolve` before any write and **MUST** follow [read-write-timing.md](read-write-timing.md) before Task/explore and exploratory repo research.

---

## A. Always Load (every memory operation)

| Stage | Load / Read | Apply |
|-------|-------------|-------|
| Bucket bind | `ops/graphiti/graphiti_memory_client.py resolve`; `ops/graphiti/group_registry.yaml` | Repo `group_id`; fail-closed if readonly when writing |
| Who / role | `environment/agents/agent_registry.yaml` (this surface’s agent) | `agent_id`, `role`, `source`, token env — not `group_id` |
| Planes | `environment/agents/docs/MEMORY_TOPOLOGY.md` | Tunnel vs HTTPS; do not conflate |
| Timing | [read-write-timing.md](read-write-timing.md) | When to search / write |
| Identity matrix | [identity-and-buckets.md](identity-and-buckets.md) | Read fan-in vs write target |
| Retrieval / write law | `rules/03-graphiti-memory.mdc`, `rules/87-cursor-memory-kernel.mdc` | Order + atomic T2 |
| Layer boundary | `rules/97-graph-layer-boundary.mdc` | Structural ≠ episodic |
| Gates / forbid groups | `rules/98-graphiti-memory-gate.mdc` | `main`/`default`/`test`; workspace write block |
| Temporal / conflicts | `rules/99-graphiti-temporal.mdc` | Search-before-write; GMP conflicts |
| T0 resume | `ops/graphiti/MEMORY_BANK_POLICY.md`; `memory-bank/activeContext.md` | Local resume SSOT |
| Cursor CLI | `ops/graphiti/graphiti_memory_client.py` | Default IDE path (tunnel `:8100`) |

---

## B. Prefer when available (control plane)

| Trigger | Load | Use |
|---------|------|-----|
| `l9-memory` on PATH / HTTPS plane | Upstream skill: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/skill/SKILL.md | Operating sequence: health → resolve → search/hydrate → conflicts/phase-lock → write |
| Cursor MCP managed install | Upstream `docs/CURSOR_INSTANTIATION.md` | `l9-memory client cursor {inspect,install,verify}` — do not hand-edit mcp.json |
| Package docs | Upstream `ARCHITECTURE.md`, `RUNBOOK.md`, `AGENTS.md` | Only when operating/debugging the control plane itself |

Do **not** vendor those bodies into this pack.

---

## C. Conditional Load

| Trigger | Load | Use |
|---------|------|-----|
| Multi-agent / shared task | `environment/agents/docs/WORK_CLAIM_PROTOCOL.md` | Claim before duplicate work — uses existing admission/idempotency |
| `GRAPHITI_WRITE_GATES=1` | `ops/graphiti/graphiti_gate_lib.py`; `ops/hooks/graphiti-gate-*.sh`; `ops/graphiti/GATES-002-ACTIVATION.md` | Prefetch satisfaction before Write/Shell/subagent |
| GMP Phase 0 | client `conflicts` / `phase-lock`; rule 99 | Lock before governed mutate |
| Wiring verify | `ops/scripts/check_governance_wiring.sh` | Health of symlinks/hooks |

---

## D. Forbid — do not Load as write path / do not rebuild

| Item | Why |
|------|-----|
| Raw Neo4j / provider DB writes | Bypass MemoryService / client |
| Cursor native `update_memory` / Memories | Repo facts go to Graphiti |
| Writing `igor-workspace` via `cmd_write` | Shared workspace; CLI blocks; bootstrap edges only |
| `group_id` in `{main, default, "", test}` | Forbidden |
| Harvesting upstream ADRs into local patterns | Drift — rule 46 |
| Reimplementing MemoryService / admission / projections | Upstream owns it |
| Blind Task/explore without memory search | Timing violation |

---

## Anti-patterns

- Hardcoding `igor-workspace` as write target because prefetch mentioned it
- Treating `agent_id` as `group_id`
- Raw MCP `add_memory` without `resolve`
- Blind “research the repo” subagent when memory already has the answer
