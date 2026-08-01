---
name: refactor
version: "1.0.0"
description: "Trigger systematic refactoring/migration workflow with safety gates"
auto_chain: ynp
dag: refactoring-v1
dag_file: .cursor-commands/workflows/dags/refactoring_dag.py
---

# /refactor — Refactoring Workflow

**DAG-ENFORCED.** Execute the `refactoring-v1` DAG.

## Usage

```
/refactor                          # Begin refactoring workflow
/refactor path/to/migration.md     # With migration/requirements document
```

## Execution

Load and execute the DAG. Follow each node's `action` field in sequence.

- **DAG**: `.cursor-commands/workflows/dags/refactoring_dag.py`
- **Id**: `refactoring-v1`

The DAG contains all instructions (analyze document → cross-reference codebase → plan → batch execute → validate → commit). No separate execution file is required.
