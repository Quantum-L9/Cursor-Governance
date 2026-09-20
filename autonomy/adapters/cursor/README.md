# Cursor

**Path:** `autonomy/adapters/cursor` | **Kind:** subsystem

## Modules

### `__init__.py`

Cursor adapter configuration and request builders.

### `adapter.py`

- `def cursor_subagent_roles() -> dict[str, Any]` — Role definitions from CURSOR_SUBAGENT_ROLES.yaml, keyed by Cursor role.
- `def runs_in_background(role) -> bool` — Background policy for one autonomy role, owned by ROLES.yaml.
- `def load_cursor_config(payload) -> AdapterConfig`
- `def build_cursor_task(deployment) -> dict[str, Any]`
- `def cursor_task_json(deployment) -> str`

### `host_bridge.py`

Native Cursor host admission over the root autonomy control plane.

- `CursorHostBridge` — Thin native-Cursor host integration over :class:`AdapterOrchestrator`.
- `def lease_status(database, lease_id) -> str | None` — Terminal or live status of a root lease, or None when it does not exist.
- `def host_bind_pre_tool_use(database, token, tool_use_id) -> dict[str, Any]` — Bind a host preToolUse(Task) ``tool_use_id`` to a pending admission.
- `def host_bind_subagent_start(database) -> dict[str, Any]` — Correlate a host subagentStart to the admission bound at preToolUse.

### `mint_admission.py`

Mint one native-Cursor Task admission token.

- `def mint_admission() -> dict[str, Any]` — Return the ``create_admission`` payload, including ``prompt_marker``.
- `def build_parser() -> argparse.ArgumentParser`
- `def main(argv) -> int`

## Dependencies

**Internal:** `autonomy`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
