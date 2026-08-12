# memory-bank/ Policy — RETIRED (2026-08-11)

**Status:** RETIRED. Session resume SSOT is **Graphiti only** (`inject` /
PICKUP episodes via `ops/graphiti/graphiti_memory_client.py`).

Do not scaffold, read as SSOT, or write `memory-bank/` from hooks, `/end-session`,
`make pr`, or agents.

See also **ADR-0005**: one agent episodic memory (CLI + MCP transports); product
runtime graphs are out of band.

## Current contract

- **sessionStart** (`session_start_bootstrap.sh`,
  `session_start_memory_orchestrator.sh`): Graphiti health + `inject` / hydration
  only. No scaffold, no T0 excerpt.
- **sessionEnd** (`graphiti-session-end.sh`): Graphiti writes only. On failure:
  log `WARN` and exit `0` — **no** local T0 fallback.
- **`/end-session` / `l9-end-session`:** Graphiti PICKUP + learnings only.
- **`make pr` handoffs:** `.l9/pr/pr-remediation-handoff.json` (not memory-bank).
- **`setup_workspace_symlinks.sh`:** does **not** create or copy `memory-bank/`.
- **`graphiti_scaffold_memory_bank`:** deprecated no-op in
  `ops/hooks/graphiti_common.sh`.
- **`_read_memory_bank` / inject:** no-op (returns empty).

## Residual trees

If a consumer still has a local `memory-bank/` directory, treat it as accidental
archival residue. Prefer delete after any durables were migrated via Graphiti CLI.
Wiring checks WARN if present; PASS when absent.

## Template

`ops/graphiti/memory-bank-template/` is archival. See `RETIRED.md` there — do not
copy templates into workspaces.
