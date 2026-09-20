# Validation

**Path:** `autonomy/validation` | **Tier:** discovered

## Purpose

Compiled graph validation for the L9 autonomy control plane.



## Components

### `GoldenTraceValidator`

No description

- File: `autonomy/validation/golden_trace.py` (L7–38)
- Methods: `validate`

### `Finding`

No description

- File: `autonomy/validation/graph_linter.py` (L19–27)
- Methods: `render`

### `GraphLinter`

No description

- File: `autonomy/validation/graph_linter.py` (L30–443)
- Methods: `lint`, `assert_valid`

### `PipelineSimulator`

No description

- File: `autonomy/validation/simulator.py` (L10–187)
- Methods: `simulate`

## Functions

- `def main() -> int`
- `def main() -> int`
- `def main() -> int`
- `def main() -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `autonomy.errors`, `autonomy.models`, `autonomy.runtime.claims`, `collections`, `collections.abc`, `dataclasses`, `typing`

<!-- l9-module-readme: generated-from-ast -->
