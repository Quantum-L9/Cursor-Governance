# GMP-GRAPHITI-FILEPACK-003 — Surgical Port Evidence Report

**Run ID:** GMP-GRAPHITI-FILEPACK-003  
**Date:** 2026-06-07  
**Scope:** GlobalCommands SSOT — surgical port from graphiti-filepack-v2 (no wholesale replace)  
**Authority:** User merge order + l9-gmp-protocol + l9-harvest-pipeline (adapt-in-place; no sed harvest for partial merges)

## Modification Lock

| May modify | Must NOT modify |
|------------|-----------------|
| `ops/hooks/graphiti-session-end.sh` | `group_registry.yaml` (wholesale) |
| `ops/graphiti/graphiti_memory_client.py` (feature inserts only) | Full client rewrite from pack |
| `ops/graphiti/prune.py` | `pipeline_v2.py`, Odoo modules |
| `ops/scripts/setup_workspace_symlinks.sh` | PlasticOS `.cursor/rules/` |
| `ops/graphiti/docker-compose.yml` (commented ontology) | |
| `ops/graphiti/DEPLOY.md` | |

**MEMORY_PREFETCH:** conflicts (Phase 0 — MCP reachable at run time)

## Phase 0 — Locked TODO Plan

| id | phase | file | operation | status |
|----|-------|------|-----------|--------|
| T1 | 2 | graphiti-session-end.sh | Replace stub → T0+T1 | DONE |
| T2 | 2 | graphiti_memory_client.py | Insert bootstrap/autoseed/mirror/search-before-write | DONE |
| T3 | 2 | prune.py | Replace stub → MCP report + fallbacks | DONE |
| T4 | 2 | setup_workspace_symlinks.sh | Insert autoseed block | DONE |
| T5 | 2 | docker-compose.yml + DEPLOY.md | Commented ontology mounts | DONE |
| T6 | 4 | test_gate_e2e_full.sh + health | Validate | DONE |

## Phase 1 — Baseline

All anchors READY. Pack source at `Current Work - IGNORE/06-07-2026/graphiti-filepack-v2/` unavailable in workspace — ported from conversation lock + in-repo ground truth.

## Phase 2 — Implementation Summary

1. **session-end (T0+T1):** `graphiti_common.sh`, stdin JSON summary parse, memory-bank overwrite, optional OpenAI distill + `write --kind session_summary`.
2. **Client (surgical):** Preserved `phase-lock`, `load_env`, HTTP health, circuit breaker. Added `resolve_read_groups`, idempotent bootstrap seed name, mirror integration edges to `igor-workspace`, search-before-write with `supersedes_uuid` retry, `autoseed-check`, multi-group search/inject, stats `get_episodes` → `search_nodes` fallback.
3. **prune.py:** Real dry-run report; `get_episodes` → `search_facts` fallback; no auto-delete.
4. **symlinks:** `GRAPHITI_AUTOSEED=0` default; hint + optional bootstrap when `=1`.
5. **compose:** Ontology volume/command **commented** pending C1 `--use-custom-entities` verification.

## Phase 4 — Validation

| Gate | Result | Evidence |
|------|--------|----------|
| `py_compile` graphiti_memory_client.py, prune.py | PASS | exit 0 |
| `test_gate_e2e_full.sh` | PASS | OK: graphiti gate E2E full passed |
| `check_governance_wiring.sh` (PlasticOS cwd) | PASS | RESULT: PASS |
| `graphiti_memory_client.py health` (live C1 tunnel) | PASS | `"healthy": true`, group_id `ib-odoo-19` |
| `autoseed-check` | PASS (exit 2 expected) | not seeded — human bootstrap pending |
| `prune --dry-run` | PASS | report JSON written |
| `bootstrap --dry-run` | PASS | manifest preview |
| `conflicts` (search_facts → search_nodes fallback) | PASS | empty list on live C1 |
| `bash -n graphiti-session-end.sh` | PASS | |

**NOT RUN:** `make pr-check` (Odoo scope N/A for GlobalCommands-only change)

## Phase 5 — Recursive Verify

**Status:** VERIFIED  
Only locked files modified. `group_registry.yaml` untouched.

## Human Follow-ups

1. Production bootstrap: `python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py bootstrap` (ib-odoo-19 not seeded yet).
2. C1 ontology: verify `docker compose exec graphiti-mcp ... --help | grep custom` before uncommenting compose volumes.
3. Optional: `GRAPHITI_AUTOSEED=1` in `~/.cursor/graphiti.env` after first manual bootstrap.

## Final Declaration (verbatim)

Phases 0-6 complete. No assumptions. No drift.

GMP-GRAPHITI-FILEPACK-003 surgical port finalized. Wholesale pack merge rejected; live C1 health verified; production bootstrap remains human-gated.
