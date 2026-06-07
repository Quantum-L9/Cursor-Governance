<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [confirm-wiring, dag]
status: active
/L9_META -->

# Confirm Wiring

DAG: `confirm-wiring-v1` — `.cursor-commands/workflows/dags/confirm_wiring_dag.py`

```
/confirm-wiring path/to/file.py
/confirm-wiring memory.consolidation
```

Flow: resolve imports → try_run → verify exports → find consumers → verify tests → report.
