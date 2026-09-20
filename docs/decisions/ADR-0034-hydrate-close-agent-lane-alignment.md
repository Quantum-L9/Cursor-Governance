# ADR-0034: SessionStart reads what sessionEnd writes, plus last-24h agent-lane facts

## Status

Accepted

## Date

2026-09-19

## Supersedes

Nothing. Companion to ADR-0030 / ADR-0033. Does not change who may write.

## Context

Three memory paths existed and did not line up:

1. **sessionEnd** writes a typed `ContinuationCapsuleV2` (`ingest_candidate` +
   `session_continuation` tag) whose objective was `Continue work in {folder}`,
   then a META `memory.close` the next SessionStart ignores.
2. **SessionStart** hydrates with task `Resume session in {folder}`, then
   searches `--tag session_continuation`. Those two objective strings produce
   different `task_signature` values when local session state is missing, so
   a just-written capsule is only reachable via `repository_fallback`.
3. **Mid-session `memory.write_agent`** lands in the same namespace immediately
   (ADR-0033) but SessionStart never asked for it. The package planner drops
   `relevance<=0` unless a tag selector is set, so a fourth search using the
   session-objective string still hid those writes.

The owner chose *enrich the capsule* over a retrieval-only path or a record-id
index: close should fold high-leverage last-24h agent writes into the capsule
the next agent actually resumes, and SessionStart should also prefetch those
same writes so a session that never closed still sees them.

Constraints that stay in force:

- Do not constrain `write_agent`.
- 24h prefetch is scoped to the current repository write-namespace hint.
  No cross-repo grants. No invented Manus connector.
- Cursor-Governance does not open sqlite (INV-03). Classification is over
  the receipt the control plane already returned.

## Decision

1. **One session-task string.** `session_task_objective(project_name)` returns
   `Continue work in {name}` and is the only string SessionStart hydrate and
   sessionEnd close use for the task / capsule objective.
2. **SessionStart call 4.** After health + hydrate + tagged continuation
   search, `canonical_hydrate` searches the primary namespace with
   `--recorded-after <now-24h>` and no tags. Hits are filtered by
   `ops/memory/agent_lane.py` (hook capsules, META closes, and
   Cursor-Governance producers are excluded). Failure is a warning, never a
   degraded SessionStart.
3. **sessionEnd enriches the capsule.** The same 24h agent-lane search runs
   under the session-end envelope (`search` is an allowed read). Decisions,
   unfinished work, and file paths from those hits are folded into the
   capsule before `ingest_candidate`. A refused search leaves the heuristic
   pickup unchanged.
4. **Surfaces share the namespace.** Cursor, Claude Code, and any other
   principal that writes into the repository namespace can read each other's
   agent-lane facts through this prefetch. Authorization stays memory's.

## Consequences

- `search_queries_used` / `CanonicalHydration.calls` is 4 on a healthy
  SessionStart with a write-namespace hint (was 3).
- session-end envelopes gain `search` (read). They do not gain a new write.
- Live 24h recall requires the bound `l9-graphite-memory` pin to accept
  `--recorded-after` and skip the relevance drop for that selector
  (ADR-0035). Until that pin lands, call 4 fail-opens and the capsule still
  aligns on the unified objective.

## Rollback

Revert `session_task_objective` call sites, the fourth search, the session-end
enrichment, and the envelope `search` additions. Capsules already written
under the unified objective remain valid.
