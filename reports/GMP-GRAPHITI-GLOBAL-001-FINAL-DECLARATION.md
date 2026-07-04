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

---

## Status Update — 2026-06-30 (read-only re-diagnosis, this workspace)

A follow-up read-only GMP diagnosis (`GMP-Report-GRAPHITI-20260630.md`, companion `GMP-Report-DIAG-20260630-system-diagnosis.md`) found the deployment has **regressed from the state validated here**. Do not treat the "Validation (local)" section above as current live status.

- **Then (this doc, 2026-06-06):** offline group resolution + gate self-test only — no live VPS health check performed.
- **Then (`GMP-GRAPHITI-FILEPACK-003.md`, 2026-06-07):** `health` → `"healthy": true` against a live **C1** tunnel, group `ib-odoo-19`.
- **Now (2026-06-30, against `46.62.243.82` / port 8100):** `health` → `"healthy": false`. Tunnel/LaunchAgent/liveness (`/healthcheck`) all OK, but the **MCP tool plane 404s** at `/mcp` and `/mcp/` — `search`, `stats`, `write` (non-dry-run) all fail. Verdict: `CRITICAL`.
- The `GRAPHITI_MEMORY_ENABLED=1` / `GRAPHITI_WRITE_GATES=0` flags from this doc are still in effect on the diagnosed machine (confirmed 2026-06-30).

See `GMP-Report-GRAPHITI-20260630.md` for the full G1–G16 evidence matrix and `GRAPHITI GAPS TO FILL.md` for the actionable remediation checklist. Smallest next action: restart the Graphiti MCP server on the VPS so `/mcp/` serves the tool plane, then re-run `health` until `healthy:true`.
