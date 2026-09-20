# Operations

**Path:** `environment/agents/generated-data/operations` | **Tier:** discovered

## Purpose

Operational health, status, replay, and dead-letter controls.



## Components

### `HealthCheck`

No description

- File: `environment/agents/generated-data/operations/health.py` (L27–39)
- Methods: `to_dict`

## Functions

- `def redact(value) -> Any`
- `def main() -> int`
- `def run_health() -> dict[str, Any]`
- `def status_payload(store) -> dict[str, Any]`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `collections.abc`, `dataclasses`, `json`, `module_loader`, `os`, `pathlib`, `receipts`, `shlex`, `state_store`, `sys`, `typing`

<!-- l9-module-readme: generated-from-ast -->
