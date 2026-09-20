# Scripts

**Path:** `skills/l9-cli-optimization/scripts` | **Tier:** discovered

## Purpose

Build a deterministic optimization CLI PR commit pack from a Git worktree.



## Components

### `PackError`

Raised when the pack cannot be built safely.

- File: `skills/l9-cli-optimization/scripts/build_commit_pack.py` (L106–107)
- Methods: _none_

### `PackError`

No description

- File: `skills/l9-cli-optimization/scripts/build_flag_activation_pack.py` (L43–44)
- Methods: _none_

### `ValidationError`

No description

- File: `skills/l9-cli-optimization/scripts/validate_commit_pack.py` (L65–66)
- Methods: _none_

## Functions

- `def schema_validate(instance, schema_filename, label) -> None` — Validate an instance against a bundled JSON Schema. jsonschema is a hard
- `def improvement_from_measurements(baseline_value, candidate_value, direction)` — Recompute improvement percent from the two measurements with metric
- `def run(command, cwd) -> subprocess.CompletedProcess[str]`
- `def sha256_bytes(data) -> str`
- `def sha256_file(path) -> str`
- `def load_spec(path) -> dict[str, Any]`
- `def require_string(data, key, prefix) -> str`
- `def safe_relative(value) -> Path`
- `def validate_measurement(data, label) -> None`
- `def calculate_leverage_score(dimensions) -> float`
- `def leverage_decision(score) -> str`
- `def validate_revision_synthesis(spec, optimization) -> None`
- `def validate_wiring(spec, optimization) -> None`
- `def validate_spec(spec) -> None`
- `def ensure_git_repo(repo_root) -> None`
- `def is_tracked(repo_root, relative) -> bool`
- `def build_patch(repo_root, base_ref, changed_files) -> bytes`
- `def under_root(root, path) -> Path` — Resolve ``path`` and require it stays under ``root`` (commonpath gate).
- `def write_text(root, path, content) -> None` — Write ``path`` only after confirming it resolves under ``root``.
- `def created_utc(spec) -> str`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `ast`, `build_commit_pack`, `datetime`, `difflib`, `flag_inventory`, `gzip`, `hashlib`, `io`, `json`, `os`, `pathlib`, `re`, `route_optimize`, `scan_capabilities`, `shlex`, `shutil`, `statistics`, `subprocess`, `sys`, `tarfile`, `tempfile`, `time`

<!-- l9-module-readme: generated-from-ast -->
