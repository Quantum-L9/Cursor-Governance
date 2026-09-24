---
description: Agent memory SSOT (canonical l9-graphite-memory control plane) — retrieval authority, namespace, two lanes (agent write_agent direct; hooks bounded), temporal supersedes/conflicts
---

# Graphiti Memory (SSOT)

**Graphiti memory gate hooks ≠ consumer-repo ADR-002 Gate hub** — this rule is Cursor episodic memory only.

**Updated: 2026-08-06** *(resume-SSOT wording superseded 2026-09-06)* — Local `memory-bank/` is **deprecated/archival** (see `ops/graphiti/MEMORY_BANK_POLICY.md`). Hooks and `/end-session` do not read or write it.

**Updated: 2026-08-07** — **One agent episodic memory** (ADR-0005). CLI + MCP are transports to the same store — not two SSOTs. Product/domain stores (Odoo ORM, consumer-app graph matching/enrichment, Gate/CEG) are **out of band** and must never be treated as Cursor agent resume memory.

**Updated: 2026-08-11** — Auto hydrate/close: `sessionStart` emits `SessionHydrationPacket` (`next=` + facts) via `ops/graphiti/hydration/`; `sessionEnd` Phase A/B closes without `/end-session`. Every write requires `agent_id` (`agent=` stamp). See `docs/MEMORY_PIPELINE_MAP.md`. `/end-session` is **force-retry / offline recovery only**.

**Updated: 2026-09-06** — Memory realignment C11/C12: the sole front door is the canonical `l9-graphite-memory` control plane through `ops/memory` (`python -m ops.memory.cli`); Graphiti is a projection memory owns. `ops/graphiti/graphiti_memory_client.py` is a tombstone, no surface holds a provider URL or bearer, and `~/.cursor/graphiti.env` carries switches only. CANONICAL_LAW §8.2, ADR-0030.

**Updated: 2026-09-07** *(single-path write wording superseded 2026-09-13)* — Doctrine closure (CANONICAL_LAW §8.3, ADR-0030 items 7–9): ONE authority (`MemoryService`), ONE canonical egress (`ops/memory`), Graphiti is a downstream projection. Resume SSOT is the canonical continuation record (`ContinuationCapsuleV2`), never Graphiti `inject` / PICKUP. A model-initiated durable write is `memory.phase_lock` → `memory.write_governed` on the `l9-graphite-memory` MCP server; that lock governs memory-write consistency only and is never repository-write authority.

**Updated: 2026-09-13** — ADR-0031 / CANONICAL_LAW §8.5: ordinary / cold model writes use MCP `memory.write_agent` (no `phase_lock`). Conflict-sensitive writes remain `memory.phase_lock` → `memory.write_governed`. Agent HTTP is sealed. Identity is the shared agents door + a signed `agent_id` assertion; the human door stays private.

**Updated: 2026-09-24** — Agent memory write contract `l9.agent_memory_write.v1` (`ops/memory/AGENT_WRITE_CONTRACT.md`, schema `ops/memory/schemas/l9.agent_memory_write.v1.schema.json`): a model-authored fact is never freehand. Build its arguments with `python -m ops.memory.agent_write build` (one atomic one-line fact, canonical class `decision|insight|observation|constraint|episodic|semantic`, exactly one `agent:<id>` tag plus a topic tag, content-derived `idempotency_key`) and pass them unchanged to `memory_write_agent` (or `memory_write_governed` with `task_signature`). The agent keeps this contract itself; nothing sits in front of the tool, and `MemoryService` still decides grants and admission. Canonical classes only: `write_governed` has no alias table in 2.4.0, so `lesson` fails there.

**Updated: 2026-09-15** — ADR-0033 / CANONICAL_LAW §8.6 (two lanes, one `MemoryService`; INV-03b). "ONE canonical egress (`ops/memory`)" above means *no provider bypass*, not *all memory traffic passes through Cursor-Governance*. **Agent lane:** the ordinary write is `memory.write_agent` (MCP) or `l9-memory write`, immediately visible to the next `hydrate` / `search`; it waits on no receipt, phase, session close, PR or governance approval, and Cursor-Governance must not gate it (`memory_gate.py` exempts `l9-memory` / `ops.memory.cli`). `phase_lock` → `write_governed` is an optional conflict-sensitive pair. **Hook lane:** SessionStart / End, prefetch, PR publish and PE/SGD ingest use `MemoryControlPlaneClient(surface=…)` under `ops/config/memory-hook-envelopes.json`. Cursor-Governance holds no local memory cognition (Phase B, promotion rules, distill queue deleted at C15); sessionEnd hands the redacted excerpt to `l9-memory distill`. `graphiti_memory_client.py` is deleted (the C11 tombstone is gone); `make graphiti-health` is `make memory-readiness`.


## Retrieval authority (canonical order)

1. Rules / `AGENTS.md` — always, $0
2. Grep / Read — when path/symbol known, $0
3. **code-graph** — importers, impact, cross-module location only ($0)
4. Scoped code-graph semantic — module path required
5. **Canonical memory** (`python -m ops.memory.cli hydrate|search`) — decisions, ADRs, constraints, CI gotchas, continuation resume
6. `Unknown` — STOP; do not unscoped graph dump

## Write tiers

| Tier | Target | Trigger |
|------|--------|---------|
| T0 | `memory-bank/` | **DEPRECATED** — archival only; do not write |
| T1 | Canonical continuation capsule (`session_continuation`) | auto sessionEnd Phase A/B — budget capped |
| T2 | Cold interactive write: `memory.write_agent` (MCP `l9-graphite-memory`; no `phase_lock`; search-before-write) | model-authored ordinary lessons, insights, decisions, ADR deltas |
| T2-hs | High-stakes interactive write: `memory.phase_lock` → `memory.write_governed` (same MCP; search-before-write) | conflict-sensitive model-authored facts (concurrent writers / namespace snapshot) |
| T2-op | Operator / deterministic-adapter CLI (`python -m ops.memory.cli write`, `hydration.cli repair-write`, legacy reconciliation) | human operator, `/end-session` repair, Program Execution, reconciliation — never the model's way around T2 / T2-hs |
| T3 | Full chat ingest | **FORBIDDEN** |

## Interactive write contract (ADR-0030 items 7–9)

- **Agents MUST be able to write durable memory.** Ordinary / cold facts use `memory.write_agent {namespace, content, memory_class, tags…}` on the package-owned `l9-graphite-memory` MCP server — no SessionStart receipt and no `phase_lock`. Conflict-sensitive facts use `memory.phase_lock {namespace, task_signature}` then `memory.write_governed {namespace, content, task_signature, memory_class, tags…}`. `MemoryService` grants the lock only after a conflict check, binds the write to the namespace snapshot digest, and refuses it if the namespace moved.
- **The phase-lock is a memory-write precondition only.** It never authorizes a source edit, never serializes git, never replaces worktree / branch / publication governance (`96-multi-agent-main-bound-execution` E7/E8/E10; `98-graphiti-memory-gate`).
- **The agent lane runs only as the signed agent principal (2026-09-24).** A
  memory must name the agent that wrote it, so `ops/memory/run_memory_mcp.sh`
  mints the ADR-0031 door at MCP spawn from `L9_MEMORY_AGENT_AUTHORITY_JSON`
  (or the workstation key maps) and refuses to start the server without it;
  the anonymous Tier 3 `local-operator` fallback of the vendored
  `l9_graphite_memory-2.4.0` wheel — whose grants froze to the spawn directory
  and covered only the package's four bundled repositories — no longer runs
  (`L9_MEMORY_ALLOW_LOCAL_OPERATOR=1` is the announced operator opt-out). The
  agent's write grants are its `assigned_groups` in
  `environment/agents/agent_registry.yaml`, whichever directory the server
  starts in. Confirm cheaply with `memory.write_agent {…, dry_run: true}`:
  `namespace did not match any write grant` means the namespace is not in the
  agent's `assigned_groups`.

  **A missing grant is a bounded agent-lane limitation, not a lane swap.** A
  fact the agent lane cannot write is reported as a gap — name the namespace
  and the `dry_run` verdict — exactly like an unbound server. It is **not**
  rerouted through the operator CLI: ADR-0033 / INV-03b classifies
  `ops/memory/cli.py` as operator form. The fix is the one-line registry change
  that adds the repository to the agent's `assigned_groups`, or provisioning
  `L9_MEMORY_AGENT_AUTHORITY_JSON` when SessionStart reports the door
  UNAVAILABLE (`ops/memory/AGENT_WRITE_CONTRACT.md`).
- **No evasion.** Generic `memory.ingest` and the generic CLI `write` are not the model's alternative to `write_agent` or `write_governed`. If the MCP server is unbound, or the agent lane holds no grant for the namespace a fact belongs to (not in the agent's `assigned_groups`), the write is reported as a gap (`L9_MEMORY_INTERPRETER` / `make memory-binding`; namespace + `dry_run` verdict), not rerouted.
- **Deterministic adapters** (SessionStart hydrate, sessionEnd close, `repair-write`, reconciliation, diagnostics) use purpose-specific `ops/memory` operations over the same admission path — adapters, not second egresses.
- **No provider transport.** Neither CLI nor MCP carries a provider URL, bearer, or raw provider tool; agents never write to the provider directly.

## MUST

- Resume from sessionStart hydration (`next=`, canonical continuation record) — never treat `memory-bank/` or a Graphiti `inject` / PICKUP read as SSOT
- Every memory request names its namespace from `python -m ops.memory.cli resolve` — a request memory authorizes, never a grant Cursor holds
- Every write stamps `agent_id` (`L9_MEMORY_AGENT_ID`; Cursor=`cursor`, Claude=`claude-code`)
- Never write to `group_id=main` or `group_id=default`
- Never use Cursor `update_memory` / native Memories for repo/code facts
- Never use code-graph for episodic decisions (use canonical memory)
- Treat `python -m ops.memory.cli` and the `l9-graphite-memory` MCP server as adapters to one `MemoryService` (ADR-0005/ADR-0030); fix the binding (`make memory-binding`) instead of inventing a second stack or calling a provider directly (INV-03)
- Model-initiated ordinary writes go `memory.write_agent`; conflict-sensitive writes go `memory.phase_lock` → `memory.write_governed`; never route either through generic ingest or the operator CLI
- Never treat consumer-product runtime graphs (consumer ERP/graph / Gate) as agent episodic memory
- Do not require `/end-session` for normal X-out — hook close is the primary path

## CLI (terminal / hooks / operator only)

Use the governance locked venv and name the repository with `--workspace` —
a namespace is repository identity, never the cwd of a shell. `write` here is
the operator / deterministic-adapter path (T2-op), not the model's interactive
write:

```bash
GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
WS="${CURSOR_PROJECT_DIR:-$(pwd)}"
memcli() { (cd "$GOV" && PYTHONPATH="$GOV" "$GRAPHITI_PY" -m ops.memory.cli "$@" --workspace "${WS:-$PWD}"); }
memcli health
memcli resolve
memcli search "query"
memcli hydrate "current task"
memcli readiness --json
```

Load skill: **`l9-graphiti-memory`**

<!-- generated-from: rules/03-graphiti-memory.mdc; do-not-edit -->
