# Scripts

**Path:** `skills/l9-repository-renovation/scripts` | **Tier:** discovered

## Purpose

Public-API surface extraction and compatibility diff (AST, zero-dependency).



## Components

_No public classes in this path._

## Functions

- `def extract_surface(root) -> dict[str, Any]`
- `def diff_surface(before, after) -> dict[str, Any]`
- `def main() -> int`
- `def is_archived_rel(rel) -> bool` — True when a repo-relative path lies under a historical / non-active directory.
- `def is_test_content(path) -> bool | None` — Structurally decide whether a Python file is real test content.
- `def repo_python_modules(root, files) -> set[str]` — Top-level importable names that resolve to first-party source in the repo.
- `def conflict_marker_kind(line) -> str | None` — Classify a line as a real VCS conflict marker, or None.
- `def finding(finding_class, severity, summary, consequence, recommendation, evidence, confidence) -> dict[str, Any]`
- `def parse_pyproject(path) -> dict[str, Any]`
- `def parse_python_declared(root, pyproject) -> dict[str, list[str]]`
- `def parse_node_declared(root) -> dict[str, Any]`
- `def python_imports(root, files) -> tuple[list[str], list[dict[str, Any]]]`
- `def extract_pytest_ignores(pyproject) -> list[str]`
- `def test_files_under(path) -> list[Path]`
- `def line_evidence(root, path, line_number, text) -> dict[str, Any]`
- `def audit(root) -> dict[str, Any]`
- `def main() -> int`
- `def utc_now() -> str`
- `def load_json(path) -> Any`
- `def safe_cli_path(value) -> Path` — Resolve a CLI-supplied file path and require it to stay within the current working

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `ast`, `collections`, `collections.abc`, `common`, `datetime`, `fnmatch`, `hashlib`, `json`, `os`, `pathlib`, `py_compile`, `re`, `subprocess`, `sys`, `tempfile`, `typing`, `validate_contract`

<!-- l9-module-readme: generated-from-ast -->
