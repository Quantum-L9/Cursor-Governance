---
name: confirm-wiring
version: "2.0.0"
description: "Verify component is fully wired — no orphan refs, no runtime failures"
auto_chain: ynp
dag: confirm-wiring-v1
dag_file: .cursor-commands/workflows/dags/confirm_wiring_dag.py
---

# /confirm-wiring — Integration Audit

**DAG-ENFORCED.** Execute the `confirm-wiring-v1` DAG.

## Usage

```
/confirm-wiring core/tools/registry_adapter.py       # Verify a file
/confirm-wiring memory.consolidation                  # Verify a module
/confirm-wiring RegistryAdapter                       # Verify a component
```

## What It Does

1. **Resolve imports** — `python3 -c "from {package} import *"`
2. **Try-run** — `make try-run FILE={file}` (syntax + import + execution)
3. **Verify exports** — Check `__init__.py` exports
4. **Find consumers** — `rg` for all importers
5. **Verify tests** — Find and run tests

## Execution

```python
from .cursor_commands.workflows.dags.confirm_wiring_dag import CONFIRM_WIRING_DAG
# Follow each node's action field in sequence
```

The DAG contains all instructions. Follow each node's `action` field exactly.

## Flow

```
START → resolve_imports → try_run → verify_exports → find_consumers → verify_tests → report
```

## Key Files

- **DAG**: `.cursor-commands/workflows/dags/confirm_wiring_dag.py`
- **Try-Run**: `tools/validation/try_run.py`
- **Makefile**: `make try-run FILE=path`
