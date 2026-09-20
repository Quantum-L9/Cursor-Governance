#  Runtime

**Path:** `workflows/dags/_runtime` | **Tier:** discovered

## Purpose

Workspace-scoped durable LangGraph checkpointer.



## Components

_No public classes in this path._

## Functions

- `def checkpoint_path(dag_id) -> Path`
- `def open_checkpointer(dag_id) -> SqliteSaver`

## Exports

`open_checkpointer`

## Dependencies

`__future__`, `langgraph.checkpoint.sqlite`, `pathlib`, `sqlite3`, `workflows.dags._runtime.durable_checkpointer`

<!-- l9-module-readme: generated-from-ast -->
