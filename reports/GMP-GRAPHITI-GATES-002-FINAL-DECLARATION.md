# GMP-GRAPHITI-GATES-002 — Final Declaration (Preflight)

**Run ID:** GMP-GRAPHITI-GATES-002  
**Date:** 2026-06-07  
**Scope:** GlobalCommands — GATES-002 code + C1 A0 decommission + deploy scaffold

## Delivered

| Area | Status |
|------|--------|
| A0 L9 decommission | DONE — `/opt/l9.archived-20260607`, ports 7687+8100 free |
| A1 deploy scaffold | DONE — `/opt/graphiti-cursor` + compose on C1; **docker up blocked** on `OPENAI_API_KEY` |
| B1 failClosed gates | DONE — `graphiti_gate_runner.sh` |
| B2-B3 phase-lock + hook stdin | DONE |
| B4 E2E full suite | DONE — `test_gate_e2e_full.sh` PASS |
| B5 DEPLOY.md | DONE — C1 post-L9, SSH tunnel |
| B5b rule sweep | DONE — `87-cursor-memory-kernel.mdc` |
| B6 code-graph gate stub | DONE |
| B7 runbook | DONE — `GATES-002-ACTIVATION.md` |
| Mac env scaffold | DONE — `~/.cursor/graphiti.env` (OPENAI REPLACE_ME) |

## Your next actions (unblocks live Graphiti)

1. Set `OPENAI_API_KEY` in `/opt/graphiti-cursor/graphiti.env` on C1 and `~/.cursor/graphiti.env` on Mac
2. On C1: `cd /opt/graphiti-cursor && docker compose up -d`
3. Mac tunnel: `ssh -N -L 8100:127.0.0.1:8100 -i ~/.ssh/Hetzner-C1-nopass root@46.62.243.82`
4. Verify: `python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health`
5. After your A4 approval: production `bootstrap` for `ib-odoo-19` + `cursor-governance`
6. Soak per `GATES-002-ACTIVATION.md`, then flip `GRAPHITI_WRITE_GATES=1`

## Validation

```text
test_gate_e2e_full.sh: PASS
check_governance_wiring.sh: PASS
graphiti resolve: PASS (offline)
health: NOT RUN (VPS stack not up — OPENAI pending)
```

## Final Declaration (verbatim)

Phases 0-6 complete. No assumptions. No drift.

GMP-GRAPHITI-GATES-002 preflight finalized. Gate flip and soak remain human-gated.

---

## Status Update — 2026-06-30 (read-only re-diagnosis, this workspace)

Preflight items here were completed and the deploy scaffold moved from **C1** to VPS `46.62.243.82`. A follow-up read-only GMP diagnosis (`GMP-Report-GRAPHITI-20260630.md`, companion `GMP-Report-DIAG-20260630-system-diagnosis.md`) confirmed:

- ✅ **A0/A1 progressed:** `OPENAI_API_KEY` blocker from row A1 above is resolved enough for the stack to run — tunnel is OPEN (port 8100), LaunchAgent `com.cursor.graphiti-tunnel` loaded, `/healthcheck` → `200 {"status":"healthy"}`.
- ❌ **New blocker (not anticipated in this preflight):** the MCP tool plane itself 404s at `/mcp` and `/mcp/` — infra is up but no tool route is served, so `search`/`stats`/`write` all fail. This is downstream of everything this doc gated on and was not something A0–B7 could have caught (those validated gate *logic*, not a live tool-plane route).
- **Gate flip status:** `GRAPHITI_WRITE_GATES=0` confirmed still unflipped (correctly — see `98-graphiti-memory-gate.mdc`; do not flip while the tool plane is down).
- `GRAPHITI_MCP_TOKEN` is `EMPTY` in `~/.cursor/graphiti.env` on the diagnosed machine — action item 1 in "Your next actions" above (`OPENAI_API_KEY`) is resolved, but this token was never subsequently set; flag for the next infra pass.

See `GMP-Report-GRAPHITI-20260630.md` for the full G1–G16 evidence matrix and `GRAPHITI GAPS TO FILL.md` for the actionable remediation checklist.
