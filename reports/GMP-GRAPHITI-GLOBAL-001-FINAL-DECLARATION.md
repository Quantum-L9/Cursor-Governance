# GMP-GRAPHITI-GLOBAL-001 — Final Declaration

**Run ID:** GMP-GRAPHITI-GLOBAL-001  
**Date:** 2026-06-06  
**Scope:** GlobalCommands SSOT — Graphiti memory integration (prefetch + T0 memory-bank)  
**Companion:** GMP-GRAPHITI-GATES-002 (write gates — shipped, default off)

## Delivered

| Area | Artifact |
|------|----------|
| Phase 0 | `ops/graphiti/REUSE_MATRIX.md`, `DEPLOY.md`, `docker-compose.yml`, env/MCP examples |
| Phase 1 | `graphiti_memory_client.py`, `graphiti_gate_lib.py`, registry, ontology, domain packs, circuit breaker, rate limiter |
| Phase 2a | `session_start_memory_orchestrator.sh`, prefetch + sessionEnd T0 hooks, `hooks.json.template` |
| Phase 2b | Gate hooks (edits/shell/subagent) — `GRAPHITI_WRITE_GATES=0` default |
| Phase 3 | Rules 03/97/98/99, deprecated `03-mcp-memory.mdc`, skill `l9-graphiti-memory` |
| Phase 3b | C1 bridge deprecation (`learning_to_mcp_bridge.py`, `transcript_distiller.py`) |
| Phase 4 | `MEMORY_BANK_POLICY.md`, wiring check extensions, memory-bank scaffold in `setup_workspace_symlinks.sh` |
| Phase 4b | `test_gate_e2e.sh` |
| Phase 5 | GMP phase-contract MEMORY_PREFETCH + evidence report §7 |
| Phase 6 | This declaration |

## Validation (local)

- `python3 ops/graphiti/graphiti_memory_client.py resolve` — offline group resolution
- `bash ops/graphiti/test_gate_e2e.sh` — gate deny/allow self-test
- `bash ops/scripts/check_governance_wiring.sh <workspace>` — Graphiti section

## Human gates (not automated)

- VPS deploy per `ops/graphiti/DEPLOY.md`
- `~/.cursor/graphiti.env` with Tailscale + API secrets
- `graphiti_memory_client.py health` + `bootstrap` against live VPS
- Enable `GRAPHITI_MEMORY_ENABLED=1` after ~1–2 weeks stable prefetch
- Enable `GRAPHITI_WRITE_GATES=1` after GATES-002 soak

## Feature flags

| Flag | Default | GMP run |
|------|---------|---------|
| `GRAPHITI_MEMORY_ENABLED` | `0` | GLOBAL-001 |
| `GRAPHITI_WRITE_GATES` | `0` | GATES-002 |

## Final Declaration (verbatim)

Phases 0-6 complete. No assumptions. No drift.

GMP-GRAPHITI-GLOBAL-001 finalized.  
No further changes permitted without a new GMP run.
