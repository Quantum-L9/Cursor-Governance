# Lifecycle

**Path:** `environment/agents/lifecycle` | **Tier:** discovered

## Purpose

Cursor subagent lifecycle receipts and composed start/stop gates.



## Components

_No public classes in this path._

## Functions

- `def host_receipt_id(raw) -> str` — Map a host tool id onto the receipt alphabet.
- `def compose_subagent_start(payload) -> dict[str, Any]` — Composed subagentStart gate with durable correlation identity.
- `def compose_host_pre_tool_use(payload) -> dict[str, Any]` — Admit a native Task launch.
- `def compose_host_subagent_start(payload) -> dict[str, Any]` — Correlate a host child to its bound admission; never manufacture identity.
- `def main() -> int`
- `def compose_subagent_stop(payload) -> dict[str, Any]`
- `def main() -> int`
- `def write_json(path, body) -> dict[str, Any]`
- `def assignment_path(assignment_id) -> Path`
- `def dispatch_path(assignment_id) -> Path`
- `def return_path(assignment_id) -> Path`
- `def raw_result_path(assignment_id) -> Path`
- `def host_correlation_path(subagent_id) -> Path`
- `def host_admission_path(tool_use_id) -> Path`
- `def host_admission_lock() -> Iterator[None]` — Serialize cap check + admission write across concurrent preToolUse hooks.
- `def host_stop_path(subagent_id) -> Path`
- `def write_host_correlation(fields) -> dict[str, Any]`
- `def load_host_correlation(subagent_id) -> dict[str, Any] | None`
- `def write_host_admission(fields) -> dict[str, Any]`
- `def load_host_admission(tool_use_id) -> dict[str, Any] | None`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `collections.abc`, `contextlib`, `datetime`, `environment.agents.lifecycle`, `environment.agents.lifecycle.compose_start`, `environment.agents.lifecycle.schemas`, `environment.agents.results.receipts`, `environment.agents.runtime_paths`, `fcntl`, `hashlib`, `json`, `os`, `pathlib`, `re`, `subprocess`, `sys`, `tempfile`, `typing`

<!-- l9-module-readme: generated-from-ast -->
