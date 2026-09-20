# Scripts

**Path:** `skills/l9-idea-execute/scripts` | **Kind:** subsystem

## Modules

### `_common.py`

- `ContractError`
- `def load_data(path) -> Any`
- `def require_mapping(value, label) -> dict[str, Any]`
- `def require_list(value, label) -> list[Any]`
- `def nonempty_string(value) -> bool`
- `def canonical_json_bytes(value) -> bytes`
- `def semantic_digest(value) -> str`
- `def dump_yaml(value) -> str`
- _+1 more public symbol(s)_

### `check_adapter_capability.py`

- `def check_unit(unit, current_caps) -> dict[str, Any]`
- `def main() -> int`

### `preflight_execution_pack.py`

- `def preflight(envelope) -> dict[str, Any]`
- `def main() -> int`

### `route_execution.py`

- `def route_envelope(envelope, registry) -> dict[str, Any]`
- `def main() -> int`

### `self_test.py`

- `def envelope(reqs)`
- `def req(rid, cap, state)`
- `def find_unit(graph, topology)`
- `def caps(adapter, unit_id)`
- `def receipt_for(env, graph)`
- `def skill_section(heading) -> str`
- `def expect_contract_error(fn, needle) -> None`
- `def main() -> int`

### `validate_adapter_snapshot.py`

- `def validate_adapter_snapshot(data) -> dict[str, Any]`
- `def compare_adapter_evidence(snapshot, current) -> dict[str, Any]`
- `def main() -> int`

### `validate_envelope.py`

- `def validate_envelope(data) -> dict[str, Any]`
- `def main() -> int`

### `validate_graph.py`

- `def validate_graph(data, envelope) -> dict[str, Any]`
- `def main() -> int`

### `validate_receipt.py`

- `def validate_receipt(data, graph, envelope) -> dict[str, Any]`
- `def main() -> int`

## Dependencies

**Internal:** `_common`, `check_adapter_capability`, `preflight_execution_pack`, `route_execution`, `validate_adapter_snapshot`, `validate_envelope`, `validate_graph`, `validate_receipt`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
