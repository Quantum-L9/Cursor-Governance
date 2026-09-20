# Scripts

**Path:** `skills/l9-repo-birth/scripts` | **Kind:** subsystem

## Modules

### `package_birth_handoff.py`

Package a proven PE source snapshot for l9-repo-template without birthing it.

- `HandoffError`
- `def git(source) -> str`
- `def sha256(path) -> str`
- `def load_json(path) -> dict[str, Any]`
- `def require_digest(evidence, key) -> str`
- `def resolve_lineage_path(source, ref) -> Path`
- `def validate_evidence(evidence, source) -> tuple[str, str, str]`
- `def package() -> dict[str, Any]`
- _+1 more public symbol(s)_

### `self_test.py`

- `def run() -> None`
- `def git_init(path) -> None`
- `def write_lineage(source) -> dict[str, str]`
- `def make_source(tmp) -> tuple[Path, dict[str, str], str, str]`
- `def make_factory(tmp) -> Path`
- `def evidence_for(lineage, revision, tree) -> dict[str, object]`
- `def main() -> int`

## Dependencies

**Internal:** `package_birth_handoff`

**External:** `jsonschema`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
