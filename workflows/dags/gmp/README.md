# Gmp

**Path:** `workflows/dags/gmp` | **Tier:** discovered

## Purpose

GMP Package — Modular GMP execution DAG



## Components

### `GMPLangGraphExecutor`

Executor for GMP workflow using LangGraph.

- File: `workflows/dags/gmp/executor.py` (L22–76)
- Methods: `run`, `resume`, `get_state`, `get_mermaid`

### `GMPPhase`

GMP execution phases.

- File: `workflows/dags/gmp/state.py` (L13–27)
- Methods: _none_

### `GMPState`

State object for GMP execution.

- File: `workflows/dags/gmp/state.py` (L31–86)
- Methods: `add_message`

## Functions

- `def compile_graph(workspace)`
- `def main()` — CLI entry point.
- `def build_gmp_graph() -> StateGraph` — Build the GMP execution graph using LangGraph.
- `def route_after_scope_confirm(state) -> Literal['baseline', 'aborted']` — Route after scope confirmation.
- `def route_after_validation_confirm(state) -> Literal['memory_write', 'implement', 'aborted']` — Route after validation confirmation.

## Exports

`GMPLangGraphExecutor`, `GMPPhase`, `GMPState`, `build_gmp_graph`, `main`

## Dependencies

`__future__`, `dataclasses`, `datetime`, `enum`, `langgraph.graph`, `pathlib`, `structlog`, `typing`, `workflows.dags._runtime.durable_checkpointer`, `workflows.dags.gmp.executor`, `workflows.dags.gmp.graph`, `workflows.dags.gmp.nodes`, `workflows.dags.gmp.routing`, `workflows.dags.gmp.state`

<!-- l9-module-readme: generated-from-ast -->
