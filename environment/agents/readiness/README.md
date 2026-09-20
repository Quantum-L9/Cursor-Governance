# Readiness

**Path:** `environment/agents/readiness` | **Kind:** subsystem

## Modules

### `__init__.py`

Unified executable-peer readiness composition.

### `compose.py`

- `def execution_ready(dimensions) -> dict[str, Any]` — Cursor EXECUTION_READY = all required dimensions true.
- `def completion_evidence_ok() -> dict[str, Any]` — Controller completion evidence join (no new PE states).

### `probe_runtime.py`

- `def main() -> int`

## Dependencies

**Internal:** `environment`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
