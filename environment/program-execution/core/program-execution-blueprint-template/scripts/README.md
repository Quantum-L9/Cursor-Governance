# Scripts

**Path:** `environment/program-execution/core/program-execution-blueprint-template/scripts` | **Kind:** subsystem

## Modules

### `instantiate.py`

- `def render_tree(target, replacements) -> None`
- `def write_manifest(root) -> None`
- `def main() -> int`

### `validate_blueprint.py`

- `def load_yaml(path) -> Any`
- `def collect_ids(items, label, errors) -> set[str]`
- `def check_refs(values, valid, context, errors) -> None`
- `def check_dag(nodes, edges, errors) -> None`
- `def validate(root, mode) -> list[str]`
- `def main() -> int`

## Dependencies

**External:** `jsonschema`, `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
