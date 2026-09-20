# Session

**Path:** `workflows/session` | **Kind:** subsystem

## Modules

### `__init__.py`

L9 Session DAGs - Systematic Coding Workflows ==============================================

Exports: `GateType`, `NodeType`, `SessionDAG`, `SessionEdge`, `SessionNode`, `SessionState`, `get_session_dag`, `list_session_dags`, `register_session_dag`, `session_dag_registry`

### `interface.py`

Session DAG Interface - Core Types ==================================

- `NodeType` — Type of session node.
- `GateType` — Type of gate (decision point).
- `SessionState` — State of session execution.
- `SessionNode` — A node in the session DAG.
- `SessionEdge` — An edge connecting two nodes in the DAG.
- `SessionDAG` — A complete session workflow DAG.

### `registry.py`

Session DAG Registry ====================

- `SessionDAGRegistry` — Registry for Session DAGs.
- `def register_session_dag(dag) -> None` — Register a session DAG in the global registry.
- `def get_session_dag(dag_id) -> SessionDAG | None` — Get a session DAG by ID or name.
- `def list_session_dags() -> list[dict[str, Any]]` — List all registered session DAGs.

## Dependencies

**Internal:** `workflows`

**External:** `structlog`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
