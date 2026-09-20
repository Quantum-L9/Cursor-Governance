# Lifecycle

**Path:** `environment/agents/lifecycle` | **Kind:** subsystem

## Modules

### `__init__.py`

Cursor subagent lifecycle receipts and composed start/stop gates.

### `compose_start.py`

- `def host_receipt_id(raw) -> str` — Map a host tool id onto the receipt alphabet.
- `def compose_subagent_start(payload) -> dict[str, Any]` — Composed subagentStart gate with durable correlation identity.
- `def compose_host_pre_tool_use(payload) -> dict[str, Any]` — Admit a native Task launch.
- `def compose_host_subagent_start(payload) -> dict[str, Any]` — Correlate a host child to its bound admission; never manufacture identity.
- `def main() -> int`

### `compose_stop.py`

- `def compose_subagent_stop(payload) -> dict[str, Any]`
- `def main() -> int`

### `receipts.py`

- `def write_json(path, body) -> dict[str, Any]`
- `def assignment_path(assignment_id) -> Path`
- `def dispatch_path(assignment_id) -> Path`
- `def return_path(assignment_id) -> Path`
- `def raw_result_path(assignment_id) -> Path`
- `def host_correlation_path(subagent_id) -> Path`
- `def host_admission_path(tool_use_id) -> Path`
- `def host_admission_lock() -> Iterator[None]` — Serialize cap check + admission write across concurrent preToolUse hooks.
- _+16 more public symbol(s)_

### `schemas.py`

## Dependencies

**Internal:** `environment`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
