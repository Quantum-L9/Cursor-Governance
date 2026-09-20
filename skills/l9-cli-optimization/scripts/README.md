# Scripts

**Path:** `skills/l9-cli-optimization/scripts` | **Kind:** subsystem

## Modules

### `build_commit_pack.py`

Build a deterministic optimization CLI PR commit pack from a Git worktree.

- `PackError` — Raised when the pack cannot be built safely.
- `def schema_validate(instance, schema_filename, label) -> None` — Validate an instance against a bundled JSON Schema. jsonschema is a hard
- `def improvement_from_measurements(baseline_value, candidate_value, direction)` — Recompute improvement percent from the two measurements with metric
- `def run(command, cwd) -> subprocess.CompletedProcess[str]`
- `def sha256_bytes(data) -> str`
- `def sha256_file(path) -> str`
- `def load_spec(path) -> dict[str, Any]`
- `def require_string(data, key, prefix) -> str`
- _+30 more public symbol(s)_

### `build_flag_activation_pack.py`

Build a deterministic, review-required PR pack from a full-throttle activation

- `PackError`
- `def under_root(root, path) -> Path`
- `def build(report_path, repo_root, output_parent) -> tuple[Path, int]`
- `def main(argv) -> int`

### `flag_inventory.py`

Full-throttle flag inventory: enumerate off-by-default flags, classify each by

- `def classify_flag(name, context) -> tuple[str, str]` — Classify flipping `name` False->True. Returns (classification, reason).
- `def flip_flag(text, flag) -> str` — Deterministic single-line edit: on `flag['line']`, flip the first
- `def inventory_flags(root, overrides) -> list[dict]` — Enumerate every off-by-default flag under `root`, classify each, and
- `def summarize(rows) -> dict`
- `def main() -> int`

### `full_throttle.py`

Full-throttle activation harness: flip a repo's off-by-default flags on, prove

- `def discover_test_cmd(root) -> list[str] | None` — Best-effort discovery of the repo's own test command (no execution).
- `def under_root(root, path) -> Path`
- `def run_activation(root, test_cmd, mode, overrides) -> dict`
- `def run_all(repos, test_cmd, mode) -> dict`
- `def main() -> int`

### `measure.py`

Run a comparable before/after measurement and emit a proof block.

- `def run_once(command, capture) -> tuple[float, float | None]`
- `def measure(command, samples, capture) -> tuple[float, float | None]`
- `def main() -> int`

### `route_optimize.py`

Deterministically route an optimize CLI revision to proportional proof obligations.

- `def route(data) -> dict[str, Any]`
- `def main() -> int`

### `scan_capabilities.py`

Scan a repository for CANDIDATE underutilization, dead-wiring, and breakage.

- `def is_test_file(rel) -> bool`
- `def is_archived(rel) -> bool`
- `def is_scratch(rel) -> bool`
- `def is_excluded(rel) -> bool` — A path whose OWN contents should not be flagged as candidates (archived or
- `def iter_files(root)`
- `def python_defs_and_refs(text)` — Return (top_level_defs_without_decorators, referenced_names) for a module.
- `def python_import_modules(text) -> list[str]` — Full dotted module names imported by a module (best-effort; AST).
- `def is_migration_file(rel) -> bool` — Alembic/migration modules are invoked by the framework via file path;
- _+9 more public symbol(s)_

### `self_test.py`

Run end-to-end, deterministic, anti-drift, and negative tests.

- `def run(command, cwd) -> subprocess.CompletedProcess[str]`
- `def build_spec() -> dict[str, object]`
- `def main() -> int`

### `validate_activation_model.py`

Validate static activation and rejection contract coverage.

- `def main() -> int`

### `validate_adaptive_reasoning.py`

Validate adaptive routing, evidence ledger, schemas, and pack integration.

- `def main() -> int`

### `validate_commit_pack.py`

Validate an optimize CLI PR commit pack.

- `ValidationError`
- `def read_json(path) -> dict[str, Any]`
- `def sha256_file(path) -> str`
- `def safe_relative(value) -> bool`
- `def validate_checksums(root) -> list[str]`
- `def validate_revision_synthesis(root, manifest, plan, pr_body) -> list[str]`
- `def validate(root) -> list[str]`
- `def main(argv) -> int`

### `validate_decision_ledger.py`

Validate the adaptive execution route and evidence/decision ledger.

- `def validate_decision_contract(spec) -> list[str]`
- `def main() -> int`

_+4 further module(s) in this directory._

## Dependencies

**Internal:** `build_commit_pack`, `flag_inventory`, `route_optimize`, `scan_capabilities`, `validate_decision_ledger`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
