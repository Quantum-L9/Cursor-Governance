<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [audit, component, dag]
status: active
/L9_META -->

# Component Audit (/audit-component)

**Runtime:** none. There is no `component_audit_dag.py` in the tree and no
`component-audit-v1` registration; this mode runs from the levels below as a
read-only procedure. If it is ever given a DAG, `l9-dag-authoring` owns
authoring and registering it under `workflows/dags/`.

## Usage

```
/audit-component memory
/audit-component core
```

## Levels

1. Package export audit (`__all__` vs imports)
2. File-level wiring (consumers, tests, re-exports)
3. API instantiation (used symbols, missing APIs)

Run the levels in order. Report evidence per level; never assert wiring you did not check.
