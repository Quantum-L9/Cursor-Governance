<!-- L9_META
l9_schema: 1
parent: l9-graphiti-memory
origin: memory-playbook-v2
tags: [graphiti, memory, timing, prefetch]
status: active
version: 2.0.0
updated: 2026-08-02
/L9_META -->

# Read / write timing

When to hit memory vs grep vs subagents. Defense-in-depth: `ops/graphiti/graphiti_gate_lib.py` when `GRAPHITI_WRITE_GATES=1`. **Skill behavior is mandatory even when gates are off.**

Upstream operating sequence (control plane): https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/skill/SKILL.md — health → resolve → search/hydrate → conflicts/phase-lock → write.

Cursor CLI equivalents: `ops/graphiti/graphiti_memory_client.py` `{health,resolve,search,inject,conflicts,phase-lock,write}`.

---

## Read timing (MUST)

| Moment | Action | Why |
|--------|--------|-----|
| Session start | `health` → `inject`/`search` → read `memory-bank/activeContext.md` | Resume + prefetch |
| **Before Task / explore subagent** (repo research) | `search` or `inject` with the **task query**; cite hits in the subagent prompt | Answers are often already in memory — do not blind-research |
| **Before exploratory codebase discovery** (“how does X work here?”, unknown layout, prior decisions/lessons/CI gotchas) | Graphiti `search` **first**; then Grep/code-graph for gaps | Episodic facts belong in Graphiti |
| Path/symbol **already known** | Grep / Read first ($0) | Rule 03 — do not force memory for a known file |
| On error | `search` error/lesson before debugging from scratch | Rule 87 |
| On user correction | `search` (dedupe) then `write` lesson | Rule 87 |
| GMP Phase 0 | `conflicts` (+ `phase-lock` when gates on) | Rule 99 |

### Pre-Task / pre-explore (fail-closed)

```text
1. resolve          → record group_id + read groups
2. search "<task>"  → or inject "<task>"
3. If memory answers the question → use it; skip or narrow the Task/grep
4. If gaps remain → Task/grep/code-graph with memory hits cited in the prompt
5. NEVER launch a blind "research the repo" Task without step 2
```

---

## Write timing (MUST)

| Moment | Action | Bucket |
|--------|--------|--------|
| Durable doctrine / lesson / ADR delta lands | Proactive T2: `search` then `write --kind lesson` | **Repo** `group_id` only |
| User correction / hard-won fix | Atomic write immediately | Repo group |
| Multi-agent discrete work unit | Work-claim protocol (cite only) | `environment/agents/docs/WORK_CLAIM_PROTOCOL.md` |
| sessionEnd | T0 `memory-bank/` per MEMORY_BANK_POLICY; T1 only if `/end-session` path | Do not dual-write carelessly |

**MUST NOT** write to `igor-workspace` via CLI. Prefer CLI over raw MCP `add_memory`.

---

## Retrieval order (aligned with rule 03)

1. Rules / `AGENTS.md`
2. Grep / Read — **when path/symbol known**
3. **Graphiti** — before **exploratory** Task/grep for decisions, lessons, constraints, CI gotchas
4. code-graph — importers / impact / cross-module
5. Scoped semantic code-graph when needed
6. `Unknown` — STOP

---

## Gates (optional soak)

When `GRAPHITI_WRITE_GATES=1`, hooks deny Write/Shell/subagent until prefetch satisfied — see `graphiti_gate_lib.py`. That does **not** replace the behavioral MUST above.
