# Compiler

**Path:** `autonomy/compiler` | **Tier:** discovered

## Purpose

Action graph compilation for the L9 autonomy control plane.



## Components

### `CompiledGraph`

No description

- File: `autonomy/compiler/graph_compiler.py` (L17–92)
- Methods: `max_parallel_width`, `serial_depth`, `to_dict`

## Functions

- `def compile_graph(campaign, deployment, action_payload) -> CompiledGraph`
- `def main() -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `autonomy.errors`, `autonomy.io`, `autonomy.models`, `collections.abc`, `dataclasses`, `heapq`, `typing`

<!-- l9-module-readme: generated-from-ast -->
