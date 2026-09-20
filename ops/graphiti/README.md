# Graphiti memory client

**Path:** `ops/graphiti` | **Kind:** subsystem

## Purpose

One episodic resume store via inject / PICKUP.

## Description

Graphiti CLI, hydration, and memory-bank policy.

## Modules

### `__init__.py`

Graphiti memory ops (Cursor-primary front door).

### `graphiti_gate_lib.py`

Memory write gate logic for Cursor hooks — canonical evidence (stage C8).

- `def load_state(conv_id) -> dict` — Canonical session state for this conversation, or ``{}``.
- `def gates_enabled() -> bool`
- `def prefetch_fresh(state, ttl_minutes) -> bool`
- `def memory_ok(state, task_sig) -> bool`
- `def pre_tool_use(payload) -> dict`
- `def shell_gate(payload) -> dict`
- `def subagent_gate(payload) -> dict` — A subagent inherits the PARENT session's evidence, read-only.
- `def main() -> int`

## Dependencies

**Internal:** `git_execution_exemption`, `ops`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
