# Session

**Path:** `workflows/session` | **Tier:** discovered

## Purpose

L9 Session DAGs - Systematic Coding Workflows



## Components

### `NodeType`

Type of session node.

- File: `workflows/session/interface.py` (L20–29)
- Methods: _none_

### `GateType`

Type of gate (decision point).

- File: `workflows/session/interface.py` (L32–38)
- Methods: _none_

### `SessionState`

State of session execution.

- File: `workflows/session/interface.py` (L41–49)
- Methods: _none_

### `SessionNode`

A node in the session DAG.

- File: `workflows/session/interface.py` (L53–89)
- Methods: _none_

### `SessionEdge`

An edge connecting two nodes in the DAG.

- File: `workflows/session/interface.py` (L93–103)
- Methods: _none_

### `SessionDAG`

A complete session workflow DAG.

- File: `workflows/session/interface.py` (L107–276)
- Methods: `get_node`, `get_outgoing_edges`, `get_next_nodes`, `validate`, `to_mermaid`, `to_markdown`

### `SessionDAGRegistry`

Registry for Session DAGs.

- File: `workflows/session/registry.py` (L27–120)
- Methods: `register`, `get`, `get_by_name`, `list_all`

## Functions

- `def register_session_dag(dag) -> None` — Register a session DAG in the global registry.
- `def get_session_dag(dag_id) -> SessionDAG | None` — Get a session DAG by ID or name.
- `def list_session_dags() -> list[dict[str, Any]]` — List all registered session DAGs.

## Exports

`GateType`, `NodeType`, `SessionDAG`, `SessionEdge`, `SessionNode`, `SessionState`, `get_session_dag`, `list_session_dags`, `register_session_dag`, `session_dag_registry`

## Dependencies

`__future__`, `dataclasses`, `enum`, `structlog`, `typing`, `workflows.session.interface`, `workflows.session.registry`

<!-- l9-module-readme: generated-from-ast -->
