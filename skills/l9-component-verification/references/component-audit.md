<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [audit, component, dag]
status: active
/L9_META -->

# Component Audit (/audit-component)

**DAG:** `component-audit-v1` — `.cursor-commands/workflows/dags/component_audit_dag.py`

## Usage

```
/audit-component memory
/audit-component core
```

## Levels

1. Package export audit (`__all__` vs imports)
2. File-level wiring (consumers, tests, re-exports)
3. API instantiation (used symbols, missing APIs)

Follow DAG node `action` fields exactly.
