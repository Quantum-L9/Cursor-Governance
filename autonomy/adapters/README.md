# Adapters

**Path:** `autonomy/adapters` | **Kind:** subsystem

## Modules

### `__init__.py`

Wave 3 IDE adapter layer.

### `bridge.py`

- `JsonLineBridge` — JSON-line stdin bridge into AdapterOrchestrator.
- `def build_parser() -> argparse.ArgumentParser`
- `def main(argv) -> int`

### `conformance.py`

- `AdapterConformance`

### `contract_renderer.py`

- `def render_agent_contract() -> dict[str, Any]`

### `heartbeat_hook.py`

- `def send_heartbeat() -> dict[str, Any]`
- `def build_parser() -> argparse.ArgumentParser`
- `def main(argv) -> int`

### `orchestrator.py`

- `AdapterOrchestrator`

### `protocol.py`

- `ConformanceStatus`
- `AdapterConfig`
- `ConformanceCheck`
- `ConformanceReport`

### `tool_hook.py`

- `def infer_capability(tool_name, arguments) -> str`
- `def infer_resource(tool_name, arguments) -> str | None`
- `def pre_tool_use() -> dict[str, Any]` — Authorize one tool call through the root capability gateway.
- `def post_tool_use() -> dict[str, Any]`
- `def main(argv) -> int`

## Dependencies

**Internal:** `autonomy`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
