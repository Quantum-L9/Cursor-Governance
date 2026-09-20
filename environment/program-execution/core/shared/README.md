# Shared

**Path:** `environment/program-execution/core/shared` | **Kind:** module

## Purpose

Canonical Program Execution Blueprint identity.

## Public interface

- `BlueprintIdentityError` — Blueprint identity could not be computed from an exact manifest.
- `def manifest_path(blueprint_root) -> Path` — The canonical identity input for ``blueprint_root``.
- `def read_manifest_bytes(blueprint_root) -> bytes` — Exact ``MANIFEST.yaml`` bytes, or fail closed.
- `def compute_blueprint_digest(blueprint_root) -> str` — Lowercase SHA-256 over the exact bytes of the Blueprint's manifest.
- `def is_canonical_digest(value) -> bool` — True for the canonical 64-character lowercase hexadecimal form.

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=module -->
