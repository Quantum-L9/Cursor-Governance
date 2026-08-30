---
name: audit-component
version: "2.0.0"
description: "Audit a component for export consistency, file wiring, and API instantiation"
auto_chain: ynp
---

# /audit-component — Component wiring audit

Delegates to skill **`l9-component-verification`** (mode `audit-component`).

There is no `component_audit_dag.py` and no `component-audit-v1` registration.
This slash is a thin trigger for the skill, not a DAG.

## Usage

```
/audit-component memory          # Audit a specific package
/audit-component core            # Audit core
/audit-component                 # Discover and pick highest-priority
```

## EXECUTION

1. Read and follow skill `l9-component-verification` in mode `audit-component`.
2. Run the levels in `skills/l9-component-verification/references/component-audit.md`:
   package export (`__all__` vs imports), file-level wiring, API instantiation.
3. Report evidence per level. Auto-chain `/ynp`.

## FORBIDDEN

- Pasting a DAG body into this file
- Inventing a second audit protocol beside the skill
- Asserting wiring you did not check
