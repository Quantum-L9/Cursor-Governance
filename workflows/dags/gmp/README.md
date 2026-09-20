# GMP

**Path:** `workflows/dags/gmp` | **Kind:** subsystem

## Modules

### `__init__.py`

GMP Package — Modular GMP execution DAG

Exports: `GMPLangGraphExecutor`, `GMPPhase`, `GMPState`, `build_gmp_graph`, `main`

### `executor.py`

GMP Executor — Executor class and CLI for GMP workflow

- `GMPLangGraphExecutor` — Executor for GMP workflow using LangGraph.
- `def compile_graph(workspace)`
- `def main()` — CLI entry point.

### `graph.py`

GMP Graph — Build the GMP execution graph

- `def build_gmp_graph() -> StateGraph` — Build the GMP execution graph using LangGraph.

### `routing.py`

GMP Routing — Conditional routing functions for GMP DAG

- `def route_after_scope_confirm(state) -> Literal['baseline', 'aborted']` — Route after scope confirmation.
- `def route_after_validation_confirm(state) -> Literal['memory_write', 'implement', 'aborted']` — Route after validation confirmation.

### `state.py`

GMP State — State definition for GMP execution

- `GMPPhase` — GMP execution phases.
- `GMPState` — State object for GMP execution.

## Dependencies

**Internal:** `workflows`

**External:** `langgraph`, `structlog`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
