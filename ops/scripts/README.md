# Governance scripts

**Path:** `ops/scripts` | **Tier:** operations

## Purpose

Capability graph behind make start / make pr / make pr-check.

Wiring, publish, and hygiene CLIs used by Makefile targets.

## Components

### `HydrateVerdict`

No description

- File: `ops/scripts/classify_hydrate_state.py` (L63–75)
- Methods: `condition_line`

### `DomainOutcome`

No description

- File: `ops/scripts/claude_projection.py` (L73–92)
- Methods: `as_dict`

### `MechanicalFacts`

No description

- File: `ops/scripts/compose_pr_body.py` (L58–83)
- Methods: _none_

### `ComposeResult`

No description

- File: `ops/scripts/compose_pr_body.py` (L87–90)
- Methods: _none_

### `OperationalHealth`

Operational health status

- File: `ops/scripts/operational-oversight.py` (L27–37)
- Methods: _none_

### `AnomalyDetection`

Detected anomaly

- File: `ops/scripts/operational-oversight.py` (L41–49)
- Methods: _none_

### `OperationalOversight`

Autonomous operational oversight system

- File: `ops/scripts/operational-oversight.py` (L52–364)
- Methods: `log`, `collect_health_metrics`, `detect_anomalies`, `respond_to_anomalies`, `save_dashboard_state`, `run`

### `CommandResult`

No description

- File: `ops/scripts/reconcile_claude_commands.py` (L45–65)
- Methods: `as_dict`

### `Result`

No description

- File: `ops/scripts/reconcile_claude_l9_skills.py` (L26–46)
- Methods: `as_dict`

### `BranchFinding`

No description

- File: `ops/scripts/repo_hygiene.py` (L65–72)
- Methods: _none_

### `WorktreeFinding`

No description

- File: `ops/scripts/repo_hygiene.py` (L76–81)
- Methods: _none_

### `StashFinding`

No description

- File: `ops/scripts/repo_hygiene.py` (L85–90)
- Methods: _none_

### Shell entrypoints

- `ops/scripts/agent_worktree_start.sh`
- `ops/scripts/attribute_tree_writers.sh`
- `ops/scripts/backup_gate.sh`
- `ops/scripts/backup_to_github.sh`
- `ops/scripts/bootstrap_agent_environment.sh`
- `ops/scripts/check_governance_wiring.sh`
- `ops/scripts/classify_generated_dirtiness.sh`
- `ops/scripts/clean_pyc.sh`
- `ops/scripts/ensure_git_merge_drivers.sh`
- `ops/scripts/ensure_gov_python.sh`
- `ops/scripts/ensure_uv_environment.sh`
- `ops/scripts/ensure_workspace_wired.sh`
- `ops/scripts/export_chats.sh`
- `ops/scripts/git_merge_driver_generated.sh`
- `ops/scripts/governance_activate_fresh.sh`
- `ops/scripts/governance_sync.sh`
- `ops/scripts/install_commit_hook.sh`
- `ops/scripts/install_cursor_hooks_bootstrap.sh`
- `ops/scripts/install_export_job.sh`
- `ops/scripts/install_ide_profile.sh`

## Functions

- `def list_population(root) -> list[str]`
- `def registered_names(root) -> dict[str, set[str]]` — Names that load by identity, not import.
- `def name_reachable(rel, names) -> bool`
- `def entrypoint_hits(root, population) -> set[str]`
- `def import_one_hop(root, seeds, population) -> set[str]` — Mark population files imported by already-reachable Python modules.
- `def category_of(rel) -> str`
- `def audit(root) -> dict`
- `def render_markdown(report) -> str`
- `def main(argv) -> int`
- `def should_skip(path, root) -> bool`
- `def main() -> int`
- `def score(severity, blast, recurrence, confidence, leverage, effort) -> int`
- `def finding(fid, title, severity, evidence, impact, action) -> dict[str, Any]`
- `def utc_now() -> str`
- `def load_manifest(root) -> tuple[dict[str, Any], Path]` — Load the live rules manifest. Fail closed if rules/ or the file is missing.
- `def collect_enforcer_blobs(root) -> dict[str, str]` — Map relative path → text for the declared enforcer set plus skills/commands.
- `def coverage_for_rules(rules, blobs) -> list[dict[str, Any]]`
- `def corpus_findings(rules) -> list[dict[str, Any]]`
- `def build_report(root, manifest, manifest_path, generated_utc) -> dict[str, Any]`
- `def sha256_bytes(data) -> str`

## Exports

`ParsedRule`, `SCHEMA`, `build_entry`, `build_manifest`, `normalize_globs`, `parse_rule`, `serialize_manifest`

## Dependencies

`__future__`, `argparse`, `ast`, `breakglass_receipt`, `claude_bootstrap_receipt`, `collections`, `collections.abc`, `copy`, `dataclasses`, `datetime`, `dirtiness`, `environment.agents.runtime_paths`, `fnmatch`, `generate_commands_manifest`, `generate_rules_manifest`, `governance_refresh_receipt`, `harvest_worktree_dirt`, `hashlib`, `importlib.util`, `json`, `lib.rule_frontmatter`, `memory_aggregator`, `os`, `pathlib`

<!-- l9-module-readme: generated-from-ast -->
