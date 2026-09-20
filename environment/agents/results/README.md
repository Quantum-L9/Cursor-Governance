# Results

**Path:** `environment/agents/results` | **Kind:** subsystem

## Modules

### `__init__.py`

Canonical Result Gateway.

### `gateway.py`

- `def normalize() -> dict[str, Any]`
- `def accept() -> dict[str, Any]`
- `def accept_and_ingest() -> dict[str, Any]`

### `receipts.py`

- `def safe_receipt_id(value) -> str` — One identifier grammar for every receipt path component.
- `def acceptance_path(result_id, assignment_id) -> Path` — Acceptance receipts are keyed by ``(assignment_id, result_id)``.
- `def write_acceptance(body) -> dict[str, Any]`
- `def load_acceptance(result_id, assignment_id) -> dict[str, Any] | None`

## Dependencies

**Internal:** `environment`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
