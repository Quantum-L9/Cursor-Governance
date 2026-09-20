# Shared

**Path:** `environment/program-execution/core/shared` | **Tier:** discovered

## Purpose

Canonical Program Execution Blueprint identity.



## Components

### `BlueprintIdentityError`

Blueprint identity could not be computed from an exact manifest.

- File: `environment/program-execution/core/shared/blueprint_identity.py` (L52–53)
- Methods: _none_

## Functions

- `def manifest_path(blueprint_root) -> Path` — The canonical identity input for ``blueprint_root``.
- `def read_manifest_bytes(blueprint_root) -> bytes` — Exact ``MANIFEST.yaml`` bytes, or fail closed.
- `def compute_blueprint_digest(blueprint_root) -> str` — Lowercase SHA-256 over the exact bytes of the Blueprint's manifest.
- `def is_canonical_digest(value) -> bool` — True for the canonical 64-character lowercase hexadecimal form.

## Exports

`BlueprintIdentityError`, `DIGEST_ALGORITHM`, `DIGEST_RE`, `MANIFEST_FILENAME`, `compute_blueprint_digest`, `is_canonical_digest`, `manifest_path`, `read_manifest_bytes`

## Dependencies

`__future__`, `hashlib`, `pathlib`, `re`

<!-- l9-module-readme: generated-from-ast -->
