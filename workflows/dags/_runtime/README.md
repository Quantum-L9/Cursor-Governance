# Runtime

**Path:** `workflows/dags/_runtime` | **Kind:** subsystem

## Modules

### `__init__.py`

Exports: `open_checkpointer`

### `durable_checkpointer.py`

Workspace-scoped durable LangGraph checkpointer.

- `def checkpoint_path(dag_id) -> Path`
- `def open_checkpointer(dag_id) -> SqliteSaver`

## Dependencies

**Internal:** `workflows`

**External:** `langgraph`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
