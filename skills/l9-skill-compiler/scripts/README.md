# Scripts

**Path:** `skills/l9-skill-compiler/scripts` | **Tier:** discovered

## Purpose

Shared helpers for the l9-skill-compiler stage scripts.



## Components

_No public classes in this path._

## Functions

- `def load_json(path)` — Read a JSON document from `path`.
- `def dump(obj, path)` — Serialize `obj` as the house JSON shape, to `path` or stdout.
- `def emit(payload, path)` — Write a stage payload and return the success exit code.
- `def fail(message, code)` — Report a stage failure on stderr and return a non-zero exit code.
- `def runtime_reference_text(root) -> str` — Return control-plane text used to distinguish runtime validators from build-only validators.
- `def is_runtime_file(path, root, runtime_text) -> bool`
- `def selected_files(root) -> tuple[list[Path], list[Path]]`
- `def validate_staged_runtime(root, files) -> int`
- `def main() -> int`
- `def parse_skill_metadata(skill_md)`
- `def enumerate_live_skills(skills_dir)`
- `def tokens(text)`
- `def uninformative_tokens(live)` — Tokens every live skill shares, which therefore prove no ownership.
- `def candidates(subject, live)`
- `def load_topology_policy()` — dag_skill_ownership rules. Absent policy disables the rule, never invents one.
- `def find_owner(live, owner_role)` — The live skill declaring owner_role, if exactly one does.
- `def dag_skill_ownership_violation(subject, live, rule)` — A DAG does not justify a Skill.
- `def decide(subject, live)`
- `def main(argv)`
- `def load(path, root) -> dict[str, Any]`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `_common`, `argparse`, `ast`, `hashlib`, `json`, `os`, `pathlib`, `re`, `shutil`, `subprocess`, `sys`, `tempfile`, `typing`, `yaml`, `zipfile`

<!-- l9-module-readme: generated-from-ast -->
