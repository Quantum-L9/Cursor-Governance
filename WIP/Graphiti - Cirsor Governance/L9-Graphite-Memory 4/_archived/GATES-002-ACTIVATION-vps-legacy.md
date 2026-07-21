# GATES-002 Activation Runbook

**Run ID:** `GMP-GRAPHITI-GATES-002`  
**Host:** `46.62.243.82` `/opt/graphiti-cursor`  
**Flags:** `GRAPHITI_MEMORY_ENABLED=1`, `GRAPHITI_WRITE_GATES=0` until soak passes

## Phase checklist

| Phase | Status | Owner |
|-------|--------|-------|
| A0 L9 decommission | DONE 2026-06-07 | Human |
| A1 Graphiti deploy | BLOCKED until `OPENAI_API_KEY` in VPS `graphiti.env` | Human |
| A2 Mac tunnel + env | Scaffold ready | Human |
| B1–B7 agent code | DONE | Agent |
| A4 production bootstrap | After health green | Human approves |
| A6 gate flip | After soak | Human |

## Soak criteria (all required before `GRAPHITI_WRITE_GATES=1`)

- [ ] `health` green 7 consecutive days (or 3 aggressive)
- [ ] 3+ sessions/repo with fresh `prefetch_ts` in `~/.cursor/graphiti-state/*.json`
- [ ] Zero false Write denies (manual log)
- [ ] `stats --group ib-odoo-19` + `cursor-governance` show RepoManifest
- [ ] `conflicts` empty or documented
- [ ] VPS down test: memory-bank loads; cached prefetch within 30m TTL
- [ ] `test_gate_e2e_full.sh` PASS

## Gate flip

```bash
# ~/.cursor/graphiti.env
GRAPHITI_WRITE_GATES=1
```

Restart Cursor. Rollback: set to `0`.

## GMP under gates

```bash
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py conflicts
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py phase-lock
```

## Tests

```bash
bash .cursor-commands/ops/graphiti/test_gate_e2e_full.sh
bash .cursor-commands/ops/scripts/check_governance_wiring.sh "$(pwd)"
```
