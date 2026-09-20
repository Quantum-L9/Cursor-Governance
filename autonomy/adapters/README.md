# Adapters

**Path:** `autonomy/adapters` | **Tier:** discovered

## Purpose

Wave 3 IDE adapter layer.



## Components

### `JsonLineBridge`

JSON-line stdin bridge into AdapterOrchestrator.

- File: `autonomy/adapters/bridge.py` (L13–134)
- Methods: `handle`, `serve`

### `AdapterConformance`

No description

- File: `autonomy/adapters/conformance.py` (L66–238)
- Methods: `run`, `required_surface_capability_fields`, `assert_surface_capabilities`

### `AdapterOrchestrator`

No description

- File: `autonomy/adapters/orchestrator.py` (L19–364)
- Methods: `register`, `require_conformant_session`, `request_agent`, `acknowledge_agent`, `authorize_tool`, `heartbeat`, `submit_artifact`, `status`

### `ConformanceStatus`

No description

- File: `autonomy/adapters/protocol.py` (L13–15)
- Methods: _none_

### `AdapterConfig`

No description

- File: `autonomy/adapters/protocol.py` (L42–108)
- Methods: `from_dict`, `surface_capabilities`

### `ConformanceCheck`

No description

- File: `autonomy/adapters/protocol.py` (L112–116)
- Methods: _none_

### `ConformanceReport`

No description

- File: `autonomy/adapters/protocol.py` (L120–150)
- Methods: `blocking_failures`, `to_dict`

## Functions

- `def build_parser() -> argparse.ArgumentParser`
- `def main(argv) -> int`
- `def render_agent_contract() -> dict[str, Any]`
- `def send_heartbeat() -> dict[str, Any]`
- `def build_parser() -> argparse.ArgumentParser`
- `def main(argv) -> int`
- `def infer_capability(tool_name, arguments) -> str`
- `def infer_resource(tool_name, arguments) -> str | None`
- `def pre_tool_use() -> dict[str, Any]` — Authorize one tool call through the root capability gateway.
- `def post_tool_use() -> dict[str, Any]`
- `def main(argv) -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `autonomy.adapters.conformance`, `autonomy.adapters.contract_renderer`, `autonomy.adapters.orchestrator`, `autonomy.adapters.protocol`, `autonomy.errors`, `autonomy.policy_loader`, `autonomy.runtime.engine`, `autonomy.runtime.store`, `autonomy.runtime.timeutil`, `autonomy.versioning`, `collections.abc`, `dataclasses`, `enum`, `importlib.util`, `json`, `os`, `pathlib`, `re`, `sys`, `typing`, `uuid`

<!-- l9-module-readme: generated-from-ast -->
