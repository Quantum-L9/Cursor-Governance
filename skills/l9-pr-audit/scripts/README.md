# Scripts

**Path:** `skills/l9-pr-audit/scripts` | **Kind:** subsystem

## Modules

### `build_audit_bundle.py`

Validate canonical l9-pr-audit JSON and build a revision-bound remediation ZIP.

- `def load_json(path) -> dict[str, Any]`
- `def schema_dir() -> Path`
- `def schema_path() -> Path`
- `def handoff_schema_path() -> Path`
- `def manifest_schema_path() -> Path`
- `def sha256_bytes(data) -> str`
- `def sha256(path) -> str`
- `def iter_strings(value) -> Iterable[str]`
- _+33 more public symbol(s)_

### `build_change_ledger.py`

Build deterministic PR-audit census and adversarial seeds from a read-only PR snapshot.

- `def classify_artifact(path) -> str`
- `def is_test(path) -> bool`
- `def added_lines(patch) -> str`
- `def removed_lines(patch) -> str`
- `def oid(prefix) -> str`
- `def in_declared_scope(path, patterns) -> bool | None`
- `def load(path) -> dict[str, Any]`
- `def validate_snapshot(doc) -> list[str]`
- _+3 more public symbol(s)_

### `deterministic_closure.py`

Deterministic closure seed generation for l9-pr-audit v2.0.

- `def stable_id(prefix) -> str`
- `def seed_hash(payload) -> str`
- `def python_public_surfaces(content) -> dict[tuple[str, str], str]`
- `def public_surface_deltas(raw, pr, classification) -> list[dict[str, Any]]`
- `def additional_symbol_deltas(raw, pr, classification) -> list[dict[str, Any]]`
- `def patch_hunks(path, patch, pr) -> list[dict[str, Any]]`
- `def failure_edges(path, patch, pr) -> list[dict[str, Any]]`
- `def code_token_present(path, content, token) -> bool`
- _+10 more public symbol(s)_

### `execute_mutation_probe.py`

Execute one deterministic mutation probe in an isolated temporary copy.

- `def sha(path) -> str`
- `def apply_candidate(path, c) -> None`
- `def run(command, cwd, timeout) -> dict[str, Any]`
- `def main() -> int`

### `self_test.py`

Deterministic regression tests for l9-pr-audit's evidence and PR remediation handoff gates.

- `def evidence(eid, etype, revision, fact, properties, findings) -> dict[str, object]`
- `def synthetic_change_ledger() -> dict[str, object]`
- `def sync_red_team(audit) -> None`
- `def populate_v18_closures(audit, ledger) -> None`
- `def base_audit() -> dict[str, object]`
- `def assert_has(errors, needle) -> None`
- `def main() -> int`

## Dependencies

**Internal:** `build_audit_bundle`, `build_change_ledger`, `deterministic_closure`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
