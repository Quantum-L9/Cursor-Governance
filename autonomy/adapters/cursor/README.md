# Cursor

**Path:** `autonomy/adapters/cursor` | **Tier:** discovered

## Purpose

Cursor adapter configuration and request builders.



## Components

### `CursorHostBridge`

Thin native-Cursor host integration over :class:`AdapterOrchestrator`.

- File: `autonomy/adapters/cursor/host_bridge.py` (L157–299)
- Methods: `create_admission`, `bind_pre_tool_use`, `bind_subagent_start`

## Functions

- `def cursor_subagent_roles() -> dict[str, Any]` — Role definitions from CURSOR_SUBAGENT_ROLES.yaml, keyed by Cursor role.
- `def runs_in_background(role) -> bool` — Background policy for one autonomy role, owned by ROLES.yaml.
- `def load_cursor_config(payload) -> AdapterConfig`
- `def build_cursor_task(deployment) -> dict[str, Any]`
- `def cursor_task_json(deployment) -> str`
- `def lease_status(database, lease_id) -> str | None` — Terminal or live status of a root lease, or None when it does not exist.
- `def host_bind_pre_tool_use(database, token, tool_use_id) -> dict[str, Any]` — Bind a host preToolUse(Task) ``tool_use_id`` to a pending admission.
- `def host_bind_subagent_start(database) -> dict[str, Any]` — Correlate a host subagentStart to the admission bound at preToolUse.
- `def mint_admission() -> dict[str, Any]` — Return the ``create_admission`` payload, including ``prompt_marker``.
- `def build_parser() -> argparse.ArgumentParser`
- `def main(argv) -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `autonomy.adapters.cursor.adapter`, `autonomy.adapters.cursor.host_bridge`, `autonomy.adapters.orchestrator`, `autonomy.adapters.protocol`, `autonomy.policy_loader`, `autonomy.runtime.engine`, `autonomy.runtime.leases`, `autonomy.runtime.timeutil`, `collections.abc`, `importlib.util`, `json`, `os`, `pathlib`, `sqlite3`, `sys`, `typing`, `uuid`

<!-- l9-module-readme: generated-from-ast -->
