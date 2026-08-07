# memory-bank/ Policy — DEPRECATED (2026-08-06)

**Status:** deprecated. Session resume SSOT is **Graphiti** (`inject` / PICKUP
episodes via `graphiti_memory_client.py`). Hooks and `/end-session` no longer
read, scaffold, or write `memory-bank/`.

## Current contract

- **sessionStart** (`session_start_bootstrap.sh`,
  `session_start_memory_orchestrator.sh`): Graphiti health + `inject` only.
  No `append_repo_memory_bank`, no scaffold.
- **sessionEnd** (`graphiti-session-end.sh`): Graphiti `write --kind
  session_summary` only. On Graphiti disabled / unresolvable `group_id` /
  write failure: log `WARN` and exit `0` — **no** T0 fallback.
- **`/end-session` / `l9-end-session`:** Graphiti PICKUP + learnings only; on
  Graphiti failure, warn and continue Redis/handoff — do not write
  `memory-bank/`.
- **`graphiti_scaffold_memory_bank`:** deprecated no-op in
  `ops/hooks/graphiti_common.sh`.

## Existing directories

Consumer-repo `memory-bank/` trees (if present) are **archival only**. Do not
delete them from hooks. Do not treat them as resume SSOT. Agents must not
append session handoffs there.

## Historical notes (pre-cutover)

Prior policy treated `memory-bank/` as a Graphiti-unavailable fallback write
target under `$CURSOR_PROJECT_DIR/memory-bank/` (never the governance clone),
append-only, with optional repo-local gitignore negation. That path is gone.
