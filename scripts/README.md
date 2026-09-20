# Scripts

**Path:** `scripts` | **Tier:** discovered

## Purpose

Repo-root helper scripts. Importable so SessionDAGs can `from scripts…`.



## Components

### `ClassInfo`

No description

- File: `scripts/generate_subsystem_readmes.py` (L67–75)
- Methods: _none_

### `FunctionInfo`

No description

- File: `scripts/generate_subsystem_readmes.py` (L79–87)
- Methods: _none_

### `ModuleFacts`

No description

- File: `scripts/generate_subsystem_readmes.py` (L91–99)
- Methods: _none_

### Shell entrypoints

- `scripts/claude-deepseek.sh`
- `scripts/preflight.sh`
- `scripts/verify-routing.sh`

## Functions

- `def resolve_repo_root(explicit) -> Path`
- `def load_config(repo_root) -> dict[str, Any]`
- `def extract_subsystem_facts(repo_root, subsystem_path) -> ModuleFacts`
- `def render_components(facts) -> str`
- `def render_functions(facts) -> str`
- `def render_exports(facts) -> str`
- `def render_dependencies(facts) -> str`
- `def generate_readme(name, config, facts, defaults) -> str`
- `def resolve_under_root(repo_root, rel) -> Path | None` — Return the resolved directory if `rel` stays inside repo_root and is not root.
- `def is_root_readme(repo_root, dest) -> bool`
- `def is_handwritten(path) -> bool`
- `def write_readme(path, content) -> None`
- `def validate_subsystem_config(key, config, repo_root) -> list[str]`
- `def normalize_heading(text) -> str`
- `def validate_sections(repo_root, key, config, defaults) -> list[str]`
- `def list_subsystems(config) -> None`
- `def report_gaps(repo_root, config) -> int` — Print stale (missing path) and unguarded handwritten READMEs. Exit 1 on stale.
- `def select_targets(config) -> list[tuple[str, dict[str, Any]]]`
- `def main(argv) -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `ast`, `dataclasses`, `datetime`, `pathlib`, `re`, `shutil`, `sys`, `typing`, `yaml`

<!-- l9-module-readme: generated-from-ast -->
