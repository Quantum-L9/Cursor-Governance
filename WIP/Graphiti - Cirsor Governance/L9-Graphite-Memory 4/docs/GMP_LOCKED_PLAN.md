<!-- L9_META
l9_schema: 1
parent: l9-gmp-protocol
layer: execution
role: locked_todo_plan
tags: [gmp, phase0, locked_plan, l9_graphite_memory]
owner: igor_beylin
status: complete
version: 2.0.0
updated: 2026-07-05
/L9_META -->

# GMP Locked TODO Plan — L9-Graphite-Memory Roadmap Phases 1-5

**Run ID:** GMP-ROADMAP-PHASES-1-5
**Date:** 2026-07-05
**Target Branch:** main
**Scope:** Transport migration, MCP server, CI/CD, gate activation, ontology
**Status:** COMPLETE — All 22 TODOs delivered. 49 tests passing.

## Execution Summary

| Phase | TODOs | Status |
|-------|-------|--------|
| Pre-corrections | T-001, T-002, T-003 | DONE |
| Phase 1 (Zep Cloud) | T-004, T-005, T-006, T-007, T-008 | DONE |
| Phase 2 (MCP Server) | T-009, T-010, T-011, T-012, T-013, T-014 | DONE |
| Phase 3 (CI/CD) | T-015, T-016 | DONE |
| Phase 4-5 (Gates + Ontology) | T-017, T-018, T-019 | DONE |
| Polish & Deliver | T-020, T-021, T-022 | DONE |

## Verification Evidence

- **Tests:** 49 passed, 1 skipped (0.66s)
- **Imports:** All 10 modules import cleanly
- **MCP Tools:** 6 registered (search, write, health, bootstrap, phase_lock, conflicts)
- **L9_META:** 6 source files tagged
- **Sacred files:** All preserved (episode_contract, group_resolver, gate_lib, rules, hooks)
- **Stale docs:** Archived to `_archived/` (DEPLOY, GATES-002, MACHINE-ENV-POLICY)

## ADRs Consulted

- `docs/adr/ADR-001-infisical-secrets-architecture.md`
- `docs/adr/ADR-002-zep-cloud-transport.md`
- `ROADMAP.md`
- `AGENTS.md`
- `docs/RECURSIVE_ALIGNMENT_AUDIT.md`

## MODIFICATION LOCK — FINAL STATE

### Modified

- `src/l9_graphite_memory/graphiti_memory_client.py` — transport abstraction + logging
- `src/l9_graphite_memory/__init__.py` — exports updated
- `pyproject.toml` — deps, extras, entry points, pytest config
- `README.md` — updated for new architecture
- `AGENTS.md` — removed L9-Ops-MCP drift
- `ROADMAP.md` — corrections applied
- `config/mcp.json.example` — Infisical-powered config

### Created

- `src/l9_graphite_memory/transport.py` — MemoryTransport Protocol + HttpMcpTransport
- `src/l9_graphite_memory/zep_transport.py` — ZepCloudTransport
- `src/l9_graphite_memory/server.py` — MCP server (stdio + SSE)
- `scripts/write_cursor_config.py` — Cursor MCP config writer
- `scripts/write_claude_config.py` — Claude Desktop MCP config writer
- `scripts/preflight.sh` — 8-gate pre-flight check
- `scripts/install.sh` — one-shot bootstrap
- `scripts/activate_gate.sh` — gate activation for target repos
- `.github/workflows/ci.yml` — lint, typecheck, test matrix
- `.github/workflows/publish.yml` — PyPI publish on tag
- `tests/test_transport.py` — transport unit tests
- `docs/adr/ADR-002-zep-cloud-transport.md` — transport ADR
- `docs/custom-ontology.md` — ontology extension guide
- `docs/GATES-ACTIVATION.md` — gate activation runbook
- `docs/DEPLOY.md` — new deployment guide
- `QUICKSTART.md` — zero-to-running guide

### Archived (stale)

- `_archived/DEPLOY-vps-legacy.md`
- `_archived/GATES-002-ACTIVATION-vps-legacy.md`
- `_archived/MACHINE-ENV-POLICY-vps-legacy.md`

### NOT Modified (sacred)

- `src/l9_graphite_memory/graphiti_gate_lib.py` — VERIFIED UNTOUCHED
- `src/l9_graphite_memory/episode_contract.py` — VERIFIED UNTOUCHED
- `src/l9_graphite_memory/group_resolver.py` — VERIFIED UNTOUCHED
- `src/l9_graphite_memory/circuit_breaker.py` — VERIFIED UNTOUCHED
- `src/l9_graphite_memory/rate_limiter.py` — VERIFIED UNTOUCHED
- `src/l9_graphite_memory/ontology_coding.py` — VERIFIED UNTOUCHED
- `src/l9_graphite_memory/secrets.py` — VERIFIED UNTOUCHED
- `rules/*.mdc` — VERIFIED UNTOUCHED
- `hooks/*.sh` — VERIFIED UNTOUCHED
- `tests/test_gate_e2e.sh` — VERIFIED UNTOUCHED
- `tests/test_gate_e2e_full.sh` — VERIFIED UNTOUCHED
- `tests/test_secrets.py` — VERIFIED UNTOUCHED

---

## Exit

GMP run COMPLETE. All phases delivered. Zero-stub validation passed. Evidence report above.
