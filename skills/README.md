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

### `ContractError`

No description

- File: `skills/l9-idea-execute/scripts/_common.py` (L14–15)
- Methods: _none_

### `FoundryContractError`

Raised when a Foundry machine contract is malformed.

- File: `skills/l9-idea-foundry/scripts/_common.py` (L21–22)
- Methods: _none_

### `ProbeError`

No description

- File: `skills/l9-idea-foundry/scripts/probe_birth_factory.py` (L33–34)
- Methods: _none_

### `QualificationError`

No description

- File: `skills/l9-idea-foundry/scripts/qualify_birth_handoff.py` (L37–38)
- Methods: _none_

### `CompileError`

No description

- File: `skills/l9-pe-campaign-activate/scripts/compile_activation_files.py` (L58–59)
- Methods: _none_

### `BriefError`

No description

- File: `skills/l9-pe-campaign-activate/scripts/compile_brief.py` (L83–86)
- Methods: _none_

### Shell entrypoints

- `skills/l9-code-graph-rag-mcp/scripts/code_graph_batch_index.sh`
- `skills/l9-code-graph-rag-mcp/scripts/code_graph_gmp_baseline.sh`
- `skills/l9-code-graph-rag-mcp/scripts/code_graph_health.sh`
- `skills/l9-mac-storage-triage/scripts/00-diagnose.sh`
- `skills/l9-mac-storage-triage/scripts/01-summarize.sh`
- `skills/l9-mac-storage-triage/scripts/02-initialize-env.sh`
- `skills/l9-mac-storage-triage/scripts/03-validate-env.sh`
- `skills/l9-mac-storage-triage/scripts/04-plan.sh`
- `skills/l9-mac-storage-triage/scripts/05-apply.sh`
- `skills/l9-mac-storage-triage/scripts/06-verify.sh`
- `skills/l9-mac-storage-triage/scripts/07-inventory-noise.sh`
- `skills/l9-mac-storage-triage/scripts/08-focus-layout.sh`
- `skills/l9-mac-storage-triage/scripts/09-emit-findings.sh`
- `skills/l9-mac-storage-triage/scripts/actions/delete-verified-source.sh`
- `skills/l9-mac-storage-triage/scripts/actions/docker-prune-unused.sh`
- `skills/l9-mac-storage-triage/scripts/actions/empty-trash.sh`
- `skills/l9-mac-storage-triage/scripts/actions/mail-cache-remove.sh`
- `skills/l9-mac-storage-triage/scripts/actions/offload-rclone.sh`
- `skills/l9-mac-storage-triage/scripts/actions/purge-stale-caches.sh`
- `skills/l9-mac-storage-triage/scripts/actions/spotlight-exclusions.sh`

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

`__future__`, `_common`, `argparse`, `ast`, `audit_plans`, `build_commit_pack`, `capability_bind`, `check_adapter_capability`, `classify_conversion_disposition`, `classify_graph_kind`, `close_resolved_issue`, `cluster_rank`, `collections`, `collections.abc`, `common`, `compile_semantic_obligations`, `convert_session_to_langgraph`, `copy`, `dataclasses`, `datetime`, `diagnose_ref_value`, `difflib`, `doc_change`, `doc_llms`
