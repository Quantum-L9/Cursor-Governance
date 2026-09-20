# Results

**Path:** `environment/agents/results` | **Tier:** discovered

## Purpose

Canonical Result Gateway.



## Components

_No public classes in this path._

## Functions

- `def normalize() -> dict[str, Any]`
- `def accept() -> dict[str, Any]`
- `def accept_and_ingest() -> dict[str, Any]`
- `def safe_receipt_id(value) -> str` — One identifier grammar for every receipt path component.
- `def acceptance_path(result_id, assignment_id) -> Path` — Acceptance receipts are keyed by ``(assignment_id, result_id)``.
- `def write_acceptance(body) -> dict[str, Any]`
- `def load_acceptance(result_id, assignment_id) -> dict[str, Any] | None`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `collections.abc`, `datetime`, `environment.agents.lifecycle`, `environment.agents.results`, `environment.agents.results.adapters`, `environment.agents.runtime_paths`, `hashlib`, `importlib.util`, `json`, `os`, `pathlib`, `re`, `sys`, `tempfile`, `typing`

<!-- l9-module-readme: generated-from-ast -->
