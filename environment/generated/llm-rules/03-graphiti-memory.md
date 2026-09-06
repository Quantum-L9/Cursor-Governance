---
description: Agent memory SSOT (canonical l9-graphite-memory control plane) — retrieval authority, namespace, temporal supersedes/conflicts
---

# Graphiti Memory (SSOT)

**Graphiti memory gate hooks ≠ consumer-repo ADR-002 Gate hub** — this rule is Cursor episodic memory only.

**Updated: 2026-08-06** — Resume SSOT is **Graphiti** (`inject` / PICKUP episodes). Local `memory-bank/` is **deprecated/archival** (see `ops/graphiti/MEMORY_BANK_POLICY.md`). Hooks and `/end-session` do not read or write it.

**Updated: 2026-08-07** — **One agent episodic memory** (ADR-0005). CLI + MCP are transports to the same Graphiti / L9 shared-memory store — not two SSOTs. Product/domain stores (Odoo ORM, consumer-app graph matching/enrichment, Gate/CEG) are **out of band** and must never be treated as Cursor agent resume memory.

**Updated: 2026-08-11** — Auto hydrate/close: `sessionStart` emits `SessionHydrationPacket` (`next=` + facts) via `ops/graphiti/hydration/`; `sessionEnd` Phase A/B writes PICKUP without `/end-session`. Every write requires `agent_id` (`agent=` stamp). See `docs/MEMORY_PIPELINE_MAP.md`. `/end-session` is **force-retry / offline recovery only**.

**Updated: 2026-09-06** — Memory realignment C11/C12: the sole front door is the canonical `l9-graphite-memory` control plane through `ops/memory` (`python -m ops.memory.cli`); Graphiti is a projection memory owns. `ops/graphiti/graphiti_memory_client.py` is a tombstone, no surface holds a provider URL or bearer, and `~/.cursor/graphiti.env` carries switches only. CANONICAL_LAW §8.2, ADR-0030.


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
| T2 | Canonical `write` (search-before-write) | lessons, insights, decisions, ADR deltas |
| T3 | Full chat ingest | **FORBIDDEN** |

## MUST

- Resume from sessionStart hydration (`next=`, canonical continuation record) — never treat `memory-bank/` as SSOT
- Every memory request names its namespace from `python -m ops.memory.cli resolve` — a request memory authorizes, never a grant Cursor holds
- Every write stamps `agent_id` (`L9_MEMORY_AGENT_ID`; Cursor=`cursor`, Claude=`claude-code`)
- Never write to `group_id=main` or `group_id=default`
- Never use Cursor `update_memory` / native Memories for repo/code facts
- Never use code-graph for episodic decisions (use canonical memory)
- Treat `python -m ops.memory.cli` and the `l9-graphite-memory` MCP server as one agent-memory store (ADR-0005/ADR-0030); fix the binding (`make memory-binding`) instead of inventing a second stack or calling a provider directly (INV-03)
- Never treat consumer-product runtime graphs (consumer ERP/graph / Gate) as agent episodic memory
- Do not require `/end-session` for normal X-out — hook close is the primary path

## CLI (terminal / hooks only)

Use the governance locked venv and name the repository with `--workspace` —
a namespace is repository identity, never the cwd of a shell:

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
