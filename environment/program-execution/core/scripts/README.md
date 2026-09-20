# Scripts

**Path:** `environment/program-execution/core/scripts` | **Tier:** discovered

## Purpose

Regenerate a Program Execution integrity manifest in its own shape.



## Components

_No public classes in this path._

## Functions

- `def is_manifest_input(root, path) -> bool` — True when `path` belongs in `root`'s manifest.
- `def manifest_inputs(root) -> list[Path]`
- `def build_payload(root) -> dict[str, Any]` — The manifest document for `root`, shaped like `prior` when there is one.
- `def generate(root, schema, artifact) -> Path`
- `def main() -> int`
- `def run(command) -> None`
- `def main() -> int`
- `def manifest_ok(root) -> bool`
- `def compatible(root) -> bool`
- `def main() -> int`
- `def load(path) -> Any`
- `def child(command) -> list[str]`
- `def validate(root, mode) -> list[str]`
- `def main() -> int`
- `def canonical_json(value) -> str`
- `def digest_object(value) -> str`
- `def load_revision(path) -> dict[str, Any]`
- `def schema_errors(revision) -> list[str]`
- `def containment_errors(revision) -> list[str]`
- `def validate_revision(revision) -> list[str]`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `hashlib`, `json`, `jsonschema`, `pathlib`, `re`, `shutil`, `subprocess`, `sys`, `tempfile`, `typing`, `yaml`

<!-- l9-module-readme: generated-from-ast -->
