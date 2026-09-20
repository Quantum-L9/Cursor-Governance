# Nodes

**Path:** `workflows/dags/gmp/nodes` | **Tier:** discovered

## Purpose

GMP Nodes — All node functions for GMP DAG



## Components

_No public classes in this path._

## Functions

- `def node_start(state) -> GMPState` — Initialize GMP execution.
- `def node_memory_read(state) -> GMPState` — 🧠 MANDATORY: Read from L9 memory.
- `def node_scope_lock(state) -> GMPState` — Define TODO plan and file budget.
- `def node_user_confirm_scope(state) -> GMPState` — Gate: User confirms scope.
- `def node_baseline(state) -> GMPState` — Verify baseline conditions.
- `def node_implement(state) -> GMPState` — Execute TODO plan.
- `def node_validate(state) -> GMPState` — Run validation suite.
- `def node_user_confirm_validation(state) -> GMPState` — Gate: User confirms validation results.
- `def node_memory_write(state) -> GMPState` — 🧠 MANDATORY: Write learnings to memory.
- `def node_finalize(state) -> GMPState` — Generate GMP report using the canonical report generator script.
- `def node_end(state) -> GMPState` — End GMP execution.
- `def node_aborted(state) -> GMPState` — Handle abort.

## Exports

`node_aborted`, `node_baseline`, `node_end`, `node_finalize`, `node_implement`, `node_memory_read`, `node_memory_write`, `node_scope_lock`, `node_start`, `node_user_confirm_scope`, `node_user_confirm_validation`, `node_validate`

## Dependencies

`__future__`, `datetime`, `pathlib`, `re`, `subprocess`, `sys`, `workflows.dags.gmp.nodes.core`, `workflows.dags.gmp.state`

<!-- l9-module-readme: generated-from-ast -->
