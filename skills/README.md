# L9 skills

**Path:** `skills` | **Tier:** control_plane

## Purpose

Procedures that outrank agent-invented contracts and sit under AGENTS.md.

Task-scoped skill packs invoked by name.

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

### `Hit`

No description

- File: `skills/l9-code-maintenance/scripts/refactor_sweep.py` (L60–65)
- Methods: _none_

### `SweepResult`

No description

- File: `skills/l9-code-maintenance/scripts/refactor_sweep.py` (L69–83)
- Methods: _none_

### `ExtractError`

Fail-closed extract/apply error. ``code`` is the process exit status.

- File: `skills/l9-git-work-preserve/scripts/extract_path_union.py` (L22–27)
- Methods: _none_

### `CompileError`

No description

- File: `skills/l9-pe-campaign-activate/scripts/compile_activation_files.py` (L52–53)
- Methods: _none_

### `BriefError`

No description

- File: `skills/l9-pe-campaign-activate/scripts/compile_brief.py` (L77–80)
- Methods: _none_

### `NuggetError`

No description

- File: `skills/l9-pe-nuggets/scripts/extract_nuggets.py` (L18–19)
- Methods: _none_

### `PlanFinding`

No description

- File: `skills/l9-pipeline-audit/scripts/audit_plans.py` (L41–49)
- Methods: _none_

### `DirectTransport`

Token-in-process path. TRUSTED OPERATOR ONLY.

- File: `skills/l9-pr-remediation/scripts/sonar_fetch.py` (L59–92)
- Methods: `authenticated`, `get`

## Functions

- `def digest(data) -> str`
- `def load_report(root) -> dict[str, Any]`
- `def validate_ci_issue_files(root, report) -> None`
- `def collect(root) -> list[Path]`
- `def package(root, output) -> None`
- `def main() -> int`
- `def load(path) -> dict[str, Any]`
- `def bullet_list(values) -> str`
- `def validate_signal(signal) -> None`
- `def render(report, output_dir) -> list[Path]`
- `def main() -> int`
- `def run_command(args) -> subprocess.CompletedProcess[str]`
- `def validate_packager(root, fixture_name, expect_ci_file) -> list[str]`
- `def run(root) -> list[str]`
- `def main() -> int`
- `def validate(skill_folder) -> list[str]`
- `def main() -> int`
- `def load(path) -> Any`
- `def schema_errors(report) -> list[str]`
- `def is_forbidden_ci_path(path) -> bool`

## Exports

`__footer_meta__`, `__l9_trace__`, `count_suppressions`, `detect_languages`, `main`, `run_gates`

## Dependencies

`__future__`, `_common`, `argparse`, `ast`, `audit_plans`, `build_commit_pack`, `classify_conversion_disposition`, `classify_graph_kind`, `close_resolved_issue`, `cluster_rank`, `collections`, `collections.abc`, `common`, `compile_semantic_obligations`, `convert_session_to_langgraph`, `copy`, `dataclasses`, `datetime`, `diagnose_ref_value`, `difflib`, `doc_change`, `doc_llms`, `doc_obligations`, `doc_policy`
