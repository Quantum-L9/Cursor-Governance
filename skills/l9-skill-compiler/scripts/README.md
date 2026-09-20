# Scripts

**Path:** `skills/l9-skill-compiler/scripts` | **Kind:** subsystem

## Modules

### `_common.py`

Shared helpers for the l9-skill-compiler stage scripts.

- `def load_json(path)` — Read a JSON document from `path`.
- `def dump(obj, path)` — Serialize `obj` as the house JSON shape, to `path` or stdout.
- `def emit(payload, path)` — Write a stage payload and return the success exit code.
- `def fail(message, code)` — Report a stage failure on stderr and return a non-zero exit code.

### `package_skill.py`

Build a runtime-only skill.zip with SKILL.md at the archive root.

- `def runtime_reference_text(root) -> str` — Return control-plane text used to distinguish runtime validators from build-only validators.
- `def is_runtime_file(path, root, runtime_text) -> bool`
- `def selected_files(root) -> tuple[list[Path], list[Path]]`
- `def validate_staged_runtime(root, files) -> int`
- `def main() -> int`

### `scan_skill_topology.py`

- `def parse_skill_metadata(skill_md)`
- `def enumerate_live_skills(skills_dir)`
- `def tokens(text)`
- `def uninformative_tokens(live)` — Tokens every live skill shares, which therefore prove no ownership.
- `def candidates(subject, live)`
- `def load_topology_policy()` — dag_skill_ownership rules. Absent policy disables the rule, never invents one.
- `def find_owner(live, owner_role)` — The live skill declaring owner_role, if exactly one does.
- `def dag_skill_ownership_violation(subject, live, rule)` — A DAG does not justify a Skill.
- _+2 more public symbol(s)_

### `validate_exemplary_skill.py`

Fail-closed validation for exemplary skill intelligence artifacts.

- `def load(path, root) -> dict[str, Any]`
- `def validate(folder) -> list[str]`
- `def main() -> int`

### `validate_skill_pack.py`

Validate a standalone skill pack for structure, metadata, references, and executable scripts.

- `def load_frontmatter(path) -> tuple[dict[str, Any], str]`
- `def local_links(path) -> list[str]`
- `def validate(root, profile) -> list[str]`
- `def main() -> int`

### `validate_smart_exemplary_spec.py`

Validate a SMART exemplary spec YAML for behavioral intelligence gates.

- `def main() -> int`

## Dependencies

**Internal:** `_common`

**External:** `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
