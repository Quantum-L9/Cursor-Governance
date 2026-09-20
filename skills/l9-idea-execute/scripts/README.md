# Scripts

**Path:** `skills/l9-idea-execute/scripts` | **Tier:** discovered

## Purpose

AST-extracted module documentation.



## Components

### `ContractError`

No description

- File: `skills/l9-idea-execute/scripts/_common.py` (L14–15)
- Methods: _none_

## Functions

- `def load_data(path) -> Any`
- `def require_mapping(value, label) -> dict[str, Any]`
- `def require_list(value, label) -> list[Any]`
- `def nonempty_string(value) -> bool`
- `def canonical_json_bytes(value) -> bytes`
- `def semantic_digest(value) -> str`
- `def dump_yaml(value) -> str`
- `def assert_acyclic(nodes, edges, label) -> None`
- `def check_unit(unit, current_caps) -> dict[str, Any]`
- `def main() -> int`
- `def preflight(envelope) -> dict[str, Any]`
- `def main() -> int`
- `def route_envelope(envelope, registry) -> dict[str, Any]`
- `def main() -> int`
- `def envelope(reqs)`
- `def req(rid, cap, state)`
- `def find_unit(graph, topology)`
- `def caps(adapter, unit_id)`
- `def receipt_for(env, graph)`
- `def skill_section(heading) -> str`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `_common`, `argparse`, `check_adapter_capability`, `copy`, `hashlib`, `json`, `pathlib`, `preflight_execution_pack`, `route_execution`, `sys`, `typing`, `validate_adapter_snapshot`, `validate_envelope`, `validate_graph`, `validate_receipt`

<!-- l9-module-readme: generated-from-ast -->
