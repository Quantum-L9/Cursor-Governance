# Scripts

**Path:** `environment/program-execution/core/program-execution-controller-template/scripts` | **Kind:** subsystem

## Modules

### `instantiate.py`

- `def write_manifest(root) -> None`
- `def main() -> int`

### `pec.py`

### `run_negative_tests.py`

- `def run(cmd, success) -> subprocess.CompletedProcess[str]`
- `def main() -> int`

### `validate_controller.py`

- `def load_yaml(path) -> Any`
- `def validate(root, mode) -> list[str]`
- `def main() -> int`

## Dependencies

**Internal:** `pec`

**External:** `jsonschema`, `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
