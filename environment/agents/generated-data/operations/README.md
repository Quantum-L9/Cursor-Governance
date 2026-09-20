# Operations

**Path:** `environment/agents/generated-data/operations` | **Kind:** subsystem

## Modules

### `__init__.py`

Operational health, status, replay, and dead-letter controls.

### `dead_letter.py`

- `def redact(value) -> Any`
- `def main() -> int`

### `health.py`

- `HealthCheck`
- `def run_health() -> dict[str, Any]`
- `def main() -> int`

### `replay.py`

- `def main() -> int`

### `status.py`

- `def status_payload(store) -> dict[str, Any]`
- `def main() -> int`

## Dependencies

**Internal:** `module_loader`, `receipts`, `state_store`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
