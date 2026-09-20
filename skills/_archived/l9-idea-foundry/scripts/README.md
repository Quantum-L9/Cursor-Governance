# Scripts

**Path:** `skills/l9-idea-foundry/scripts` | **Tier:** discovered

## Purpose

Shared deterministic primitives for L9 Idea Foundry scripts.



## Components

### `FoundryContractError`

Raised when a Foundry machine contract is malformed.

- File: `skills/l9-idea-foundry/scripts/_common.py` (L21–22)
- Methods: _none_

### `ProbeError`

No description

- File: `skills/l9-idea-foundry/scripts/probe_birth_factory.py` (L33–34)
- Methods: _none_

### `QualificationError`

No description

- File: `skills/l9-idea-foundry/scripts/qualify_birth_handoff.py` (L37–38)
- Methods: _none_

## Functions

- `def sha256_bytes(data) -> str`
- `def sha256_file(path) -> str`
- `def valid_sha256(value) -> bool`
- `def canonical_json_bytes(value) -> bytes`
- `def semantic_digest(value) -> str`
- `def load_yaml(path) -> Any`
- `def load_yaml_mapping(path) -> dict[str, Any]`
- `def semantic_yaml_digest(path) -> str`
- `def require_schema(mapping, expected, label) -> None`
- `def git_output(root) -> tuple[int, str]`
- `def git_require(root) -> str`
- `def tracked_tree_records(root) -> list[dict[str, object]]`
- `def tracked_tree_digest(root) -> tuple[list[dict[str, object]], str]`
- `def artifact_entry(root, rel, semantic) -> dict[str, str]`
- `def main() -> int`
- `def main() -> int`
- `def sha256_bytes(data) -> str`
- `def path_kind(path) -> str`
- `def record_path(records, root, path, prefix) -> None`
- `def safe_extract_zip(src, dest) -> None`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `_common`, `argparse`, `hashlib`, `io`, `json`, `os`, `pathlib`, `py_compile`, `qualify_birth_handoff`, `re`, `stat`, `subprocess`, `sys`, `tarfile`, `tempfile`, `tomllib`, `typing`, `yaml`, `zipfile`

<!-- l9-module-readme: generated-from-ast -->
