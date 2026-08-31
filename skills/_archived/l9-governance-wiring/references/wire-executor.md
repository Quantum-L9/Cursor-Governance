<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [wire, executor, component]
status: active
/L9_META -->

# Wire Executor (code components)

```bash
python3 .cursor-commands/workflows/wire_executor.py <component>
```

Pipeline: discovery → analysis → plan → execute → validate → re-discovery → confirm-wiring → report → local commit (no push).

State: `.wire_executor_state.json` (`--resume`, `--reset`).

Protected files (auto-escalate to GMP): executor.py, websocket_orchestrator.py, substrate_service.py, docker-compose.yml.
