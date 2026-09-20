# Nodes

**Path:** `workflows/dags/gmp/nodes` | **Kind:** subsystem

## Modules

### `__init__.py`

GMP Nodes — All node functions for GMP DAG

Exports: `node_aborted`, `node_baseline`, `node_end`, `node_finalize`, `node_implement`, `node_memory_read`, `node_memory_write`, `node_scope_lock`, `node_start`, `node_user_confirm_scope`, `node_user_confirm_validation`, `node_validate`

### `core.py`

GMP Core Nodes — All node functions for GMP execution

- `def node_start(state) -> GMPState` — Initialize GMP execution.
- `def node_memory_read(state) -> GMPState` — 🧠 MANDATORY: Read from L9 memory.
- `def node_scope_lock(state) -> GMPState` — Define TODO plan and file budget.
- `def node_user_confirm_scope(state) -> GMPState` — Gate: User confirms scope.
- `def node_baseline(state) -> GMPState` — Verify baseline conditions.
- `def node_implement(state) -> GMPState` — Execute TODO plan.
- `def node_validate(state) -> GMPState` — Run validation suite.
- `def node_user_confirm_validation(state) -> GMPState` — Gate: User confirms validation results.
- _+4 more public symbol(s)_

## Dependencies

**Internal:** `workflows`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
