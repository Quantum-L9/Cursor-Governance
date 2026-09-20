# Graphiti hydration and legacy support

**Path:** `ops/graphiti` | **Tier:** operations

## Purpose

Support hydration and archive paths. Canonical agent memory is the l9-graphite-memory control plane reached through ops/memory (CANONICAL_LAW section 8.2); Graphiti is a projection that plane owns.

Hydration helpers, transcript archive, and redaction retained around the retired direct-Graphiti client. Not the memory front door.

## Components

_No public classes in this path._

## Functions

- `def load_state(conv_id) -> dict` — Canonical session state for this conversation, or ``{}``.
- `def gates_enabled() -> bool`
- `def prefetch_fresh(state, ttl_minutes) -> bool`
- `def memory_ok(state, task_sig) -> bool`
- `def pre_tool_use(payload) -> dict`
- `def shell_gate(payload) -> dict`
- `def subagent_gate(payload) -> dict` — A subagent inherits the PARENT session's evidence, read-only.
- `def main() -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `git_execution_exemption`, `json`, `ops.memory.session_state`, `os`, `pathlib`, `re`, `sys`

<!-- l9-module-readme: generated-from-ast -->
