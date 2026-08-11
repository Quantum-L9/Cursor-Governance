# ADR-0005: One agent episodic memory; product/domain memory is out of band

## Status

Accepted

## Date

2026-08-07

## Context

Operators and agents sometimes treat **transport names** (Graphiti CLI,
`l9-graphite-memory` / `l9-shared-memory` MCP, Cursor-labeled
`user-l9-graphite-memory`) as **separate memory products**, or conflate
**IDE/agent episodic memory** with **application runtime graphs** inside a
consumer product (for example PlasticOS / Odoo Neo4j matching, enrichment,
or Gate intelligence).

That confusion produces:

- Dual “SSOT” narratives (CLI vs MCP) that fight each other in session guidance
- Writes aimed at the wrong store (product graph treated as agent resume)
- Auth/wiring failures on one transport misread as “two memory stacks”
- PlasticOS overlay rules that sound like a second agent-memory authority

ADR-0003 already keeps **two entry points** (hook path + interactive MCP) to
**one contract**. This ADR states the complementary identity rule: those entry
points are not two memories, and product domain stores are never agent memory.

## Decision

1. **One agent episodic memory.** For Cursor / Claude Code / L9 agent surfaces,
   there is a single episodic memory authority: the Graphiti / L9 shared-memory
   service (group-scoped episodes, PICKUP, lessons, hydrate/search). Resume SSOT
   is Graphiti `inject` / PICKUP. Local `memory-bank/` remains deprecated/archival
   (see `ops/graphiti/MEMORY_BANK_POLICY.md`).

2. **Multiple transports, one store.** CLI (`graphiti_memory_client.py`), harness
   hooks, and MCP tools (`memory.*` / graphite-memory surface) are **access
   paths** to that same agent-memory contract. Prefer the governance locked-venv
   CLI for deterministic lifecycle (sessionStart / `/end-session` / GMP gates).
   Prefer MCP for mid-session ad-hoc search/write when registered and
   authenticated. A transport failure is a **wiring** problem, not permission to
   invent a second agent memory.

3. **Product / domain memory is out of band.** Runtime graphs and stores inside
   a consumer application (Odoo ORM state, PlasticOS Neo4j matching/enrichment,
   Gate/CEG intelligence, CRM sync caches, etc.) are **product systems**. They
   must not be treated as Cursor agent episodic memory, session resume SSOT, or
   substitutes for Graphiti PICKUP/lessons. Consumer-repo overlays may document
   product graph procedures; they must not redefine global agent-memory SSOT.

4. **Structural code-graph stays separate.** `code-graph-rag` answers “where in
   code?” only. It is not episodic memory (unchanged: `rules/97-graph-layer-boundary.mdc`).

## Consequences

### Positive

- Agents stop choosing between “CLI Graphiti” and “graphite MCP” as competing SSOTs
- PlasticOS / Odoo work keeps product Neo4j (and related) clearly non-agent-memory
- MCP auth failures get fixed as wiring, not as doctrine forks

### Negative / costs

- Operators must keep MCP registration and bearer identity healthy for interactive
  path (ADR-0003 readiness requirement remains)
- Product repos must not invent parallel “agent memory” stacks under new names

### Non-goals

- Does not collapse hook vs MCP entry points (ADR-0003 still stands)
- Does not replace PlasticOS ADR-002 Gate hub or product graph architecture
- Does not re-enable `memory-bank/` as resume SSOT

## Related

- ADR-0002 — memory enforcement contract
- ADR-0003 — two entry points, one contract
- ADR-0004 — hook memory client contract pin
- `rules/03-graphiti-memory.mdc`
- `rules/97-graph-layer-boundary.mdc`
- `skills/l9-graphiti-memory/SKILL.md`
