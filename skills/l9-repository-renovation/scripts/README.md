# Scripts

**Path:** `skills/l9-repository-renovation/scripts` | **Kind:** subsystem

## Modules

### `api_surface.py`

Public-API surface extraction and compatibility diff (AST, zero-dependency).

- `def extract_surface(root) -> dict[str, Any]`
- `def diff_surface(before, after) -> dict[str, Any]`
- `def main() -> int`

### `audit_repository.py`

- `def is_archived_rel(rel) -> bool` — True when a repo-relative path lies under a historical / non-active directory.
- `def is_test_content(path) -> bool | None` — Structurally decide whether a Python file is real test content.
- `def repo_python_modules(root, files) -> set[str]` — Top-level importable names that resolve to first-party source in the repo.
- `def conflict_marker_kind(line) -> str | None` — Classify a line as a real VCS conflict marker, or None.
- `def finding(finding_class, severity, summary, consequence, recommendation, evidence, confidence) -> dict[str, Any]`
- `def parse_pyproject(path) -> dict[str, Any]`
- `def parse_python_declared(root, pyproject) -> dict[str, list[str]]`
- `def parse_node_declared(root) -> dict[str, Any]`
- _+6 more public symbol(s)_

### `common.py`

- `def utc_now() -> str`
- `def load_json(path) -> Any`
- `def safe_cli_path(value) -> Path` — Resolve a CLI-supplied file path and require it to stay within the current working directory, so a crafted argument cannot read or write outside the working tree.
- `def write_json(path, payload) -> None`
- `def run(command) -> dict[str, Any]`
- `def iter_files(root) -> Iterable[Path]`
- `def read_text(path, limit) -> str | None`
- `def stable_id() -> str`
- _+3 more public symbol(s)_

### `compare_audits.py`

- `def summarize(findings) -> dict[str, Any]`
- `def main() -> int`

### `compile_contract.py`

- `def evidence_paths(findings) -> set[str]`
- `def detect_validation(repo, inventory) -> list[dict[str, Any]]`
- `def build_plan(contract, audit) -> str`
- `def main() -> int`

### `render_pr_body.py`

- `def command_line(record) -> str`
- `def main() -> int`

### `run_validation_matrix.py`

- `def main() -> int`

### `self_test.py`

- `def run(command, cwd, expect) -> subprocess.CompletedProcess[str]`
- `def write(path, text) -> None`
- `def load(path) -> dict`
- `def regression_ast_precision() -> None` — Lock the AST-precision behaviors: structural test-content, scope-aware first-party imports, and structural conflict markers — in both directions.
- `def regression_api_surface() -> None` — Lock the public-API compatibility gate: a removed parameter is breaking, an added optional parameter is compatible.
- `def main() -> int`

### `validate_contract.py`

- `def validate(contract) -> list[str]`
- `def main() -> int`

### `validate_exemplary_skill.py`

- `def frontmatter(skill_text) -> tuple[dict[str, str], str | None]`
- `def main() -> int`

### `validate_pr_pack.py`

- `def changed_files(repo, base_ref) -> tuple[list[str], str | None]`
- `def added_lines(repo, base_ref) -> tuple[list[dict[str, Any]], str | None]`
- `def main() -> int`

## Dependencies

**Internal:** `common`, `validate_contract`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
