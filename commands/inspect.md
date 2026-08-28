---
name: inspect
version: "5.0.0"
description: "Inspect code before it enters L9"
auto_chain: ynp
dag: inspect-v1
dag_file: workflows/dags/inspect_dag.py
---

# /inspect — Code gate

**DAG-ENFORCED.** Execute the `inspect-v1` DAG at `workflows/dags/inspect_dag.py`.

Read-only: classify → orient → structure → compliance → impact → route → report.

## Usage

```
/inspect core/tools/registry_adapter.py   # audit an existing repo file
/inspect current_work/guide.md            # gate external code in a markdown doc
```

## EXECUTION

1. Load and execute the canonical DAG. Follow each node's action exactly.
2. Auto-chain `/ynp`.

The former `l9-inspect` Skill wrapper is archived under
`skills/_archived/l9-inspect/`; the DAG always carried the protocol.
DAG lifecycle changes are owned by skill `l9-dag-authoring`.

## FORBIDDEN

- Importing ungated external code
- Writing code from this read-only gate
- Pasting a DAG body into this file
