# Scripts

**Path:** `environment/program-execution/core/scripts` | **Kind:** subsystem

## Modules

### `generate_manifest.py`

Regenerate a Program Execution integrity manifest in its own shape.

- `def is_manifest_input(root, path) -> bool` — True when `path` belongs in `root`'s manifest.
- `def manifest_inputs(root) -> list[Path]`
- `def build_payload(root) -> dict[str, Any]` — The manifest document for `root`, shaped like `prior` when there is one.
- `def generate(root, schema, artifact) -> Path`
- `def main() -> int`

### `instantiate_pair.py`

- `def run(command) -> None`
- `def main() -> int`

### `run_negative_tests.py`

- `def manifest_ok(root) -> bool`
- `def compatible(root) -> bool`
- `def main() -> int`

### `validate_pair.py`

- `def load(path) -> Any`
- `def child(command) -> list[str]`
- `def validate(root, mode) -> list[str]`
- `def main() -> int`

### `validate_replan.py`

Validate a Replan Revision against program-execution.replan.v1.

- `def canonical_json(value) -> str`
- `def digest_object(value) -> str`
- `def load_revision(path) -> dict[str, Any]`
- `def schema_errors(revision) -> list[str]`
- `def containment_errors(revision) -> list[str]`
- `def validate_revision(revision) -> list[str]`
- `def main() -> int`

## Dependencies

**External:** `jsonschema`, `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
