# Surface Analyzers

**Path:** `skills/l9-update-agent-docs/scripts/surface_analyzers` | **Kind:** subsystem

## Modules

### `__init__.py`

Deterministic operational-surface analyzers for Repo Docs.

### `makefile.py`

Deterministic Makefile operational-contract checks.

- `def analyze(root, target) -> dict[str, Any]`

### `pyproject.py`

Deterministic pyproject.toml operational-contract assessment.

- `PythonRepoPolicy` — What this repository's own authorities require of its Python surface.
- `def load_python_repo_policy(root) -> PythonRepoPolicy` — Resolve repository-native Python policy. No universal Python laws.
- `def assess_python_project(root, state, policy, text) -> list[dict[str, Any]]` — Judge observed state against repository policy.
- `def analyze(root, target) -> dict[str, Any]`

Exports: `PythonRepoPolicy`, `analyze`, `assess_python_project`, `load_python_repo_policy`

### `python_project.py`

Generic Python-project observation, free of repository policy.

- `VersionFloor` — Lowest Python minor a specifier supports, or why it cannot be named.
- `PythonProjectState` — What the project declares. No judgement, no repository knowledge.
- `def python_floor(requires_python) -> VersionFloor` — Lowest supported `major.minor`, or UNKNOWN — never a silent pass.
- `def normalize_pytest_addopts(value) -> tuple[tuple[str, ...], bool]` — Tokenize addopts. Returns the tokens and whether they resolved.
- `def pytest_ignored_paths(tokens) -> set[str]` — Paths excluded by `--ignore`, in both the `=` and split spellings.
- `def parse_collection_guards(text) -> tuple[tuple[str, ...], tuple[str, ...], bool]` — Literal `collect_ignore` / `collect_ignore_glob` from a conftest.
- `def path_is_collection_guarded(rel) -> bool`
- `def inspect_python_project(root, data) -> PythonProjectState` — Observe a parsed `pyproject.toml` plus the files it points at.

Exports: `PythonProjectState`, `VersionFloor`, `inspect_python_project`, `normalize_pytest_addopts`, `parse_collection_guards`, `path_is_collection_guarded`, `pytest_ignored_paths`, `python_floor`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
