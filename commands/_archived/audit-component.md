---
name: audit-component
version: "1.0.0"
description: "Audit a component for export consistency, file wiring, and API instantiation"
auto_chain: ynp
dag: component-audit-v1
dag_file: .cursor-commands/workflows/dags/component_audit_dag.py
---

# /audit-component — Component Wiring Audit

**DAG-ENFORCED.** Execute the `component-audit-v1` DAG.

## Usage

```
/audit-component memory          # Audit a specific package
/audit-component core            # Audit core
/audit-component                 # Discover and pick highest-priority
```

## What It Does

1. **Level A** — Package export audit (`__all__` vs imports)
2. **Level B** — File-level wiring (consumers, tests, re-exports)
3. **Level C** — API instantiation (used symbols, missing APIs)

## Execution

```python
from .cursor-commands.workflows.dags import COMPONENT_AUDIT_DAG
# Follow each node's action field in sequence
```

The DAG contains all instructions. Follow each node's `action` field exactly.

## Key Files

- **DAG**: `.cursor-commands/workflows/dags/component_audit_dag.py`
- **Script**: `tools/validation/audit_package_exports.py`
- **Guide**: `reports/COMPONENT_WIRING_AUDIT_GUIDE.md`
- **Confirm-Wiring**: `.cursor-commands/workflows/dags/confirm_wiring_dag.py`
