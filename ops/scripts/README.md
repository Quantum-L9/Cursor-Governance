# Governance scripts

**Path:** `ops/scripts` | **Kind:** subsystem

## Purpose

Capability graph behind make start / make pr / make pr-check.

## Description

Wiring, publish, and hygiene CLIs used by Makefile targets.

## Modules

### `audit_corpus_reachability.py`

Advisory corpus reachability audit (harvest C5).

- `def list_population(root) -> list[str]`
- `def registered_names(root) -> dict[str, set[str]]` — Names that load by identity, not import.
- `def name_reachable(rel, names) -> bool`
- `def entrypoint_hits(root, population) -> set[str]`
- `def import_one_hop(root, seeds, population) -> set[str]` — Mark population files imported by already-reachable Python modules.
- `def category_of(rel) -> str`
- `def audit(root) -> dict`
- `def render_markdown(report) -> str`
- _+1 more public symbol(s)_

### `audit_rule_references.py`

Fail-closed scan for stale references to retired/renamed Cursor rules.

- `def should_skip(path, root) -> bool`
- `def main() -> int`

### `audit_rules_corpus.py`

Produce an evidence-first, read-only audit of the global Cursor rule corpus.

- `def score(severity, blast, recurrence, confidence, leverage, effort) -> int`
- `def finding(fid, title, severity, evidence, impact, action) -> dict[str, Any]`
- `def utc_now() -> str`
- `def load_manifest(root) -> tuple[dict[str, Any], Path]` — Load the live rules manifest. Fail closed if rules/ or the file is missing.
- `def collect_enforcer_blobs(root) -> dict[str, str]` — Map relative path → text for the declared enforcer set plus skills/commands.
- `def coverage_for_rules(rules, blobs) -> list[dict[str, Any]]`
- `def corpus_findings(rules) -> list[dict[str, Any]]`
- `def build_report(root, manifest, manifest_path, generated_utc) -> dict[str, Any]`
- _+2 more public symbol(s)_

### `build_claude_skill_registry.py`

Build the deterministic L9 skill registry from governance SSOT.

- `def sha256_bytes(data) -> str`
- `def load_frontmatter(path) -> dict[str, Any]`
- `def tier_entries(manifest, tier) -> list[dict[str, Any]]`
- `def build_registry(root) -> dict[str, Any]`
- `def serialized(registry) -> str`
- `def main() -> int`

### `capture_rules_cleanup_preflight.py`

Capture a machine-readable preflight for the two-repository rule cleanup.

- `def run(repo) -> str`
- `def sha256(path) -> str | None`
- `def object_state(path) -> dict[str, Any]`
- `def repo_state(repo) -> dict[str, Any]`
- `def main() -> int`

### `check_rules_standard.py`

CI gate for docs/rules-standard.md Section 6.

- `def check_rules(root) -> tuple[list[str], list[str], int, int]` — Return (errors, warnings, always_total_bytes, files_checked).
- `def main() -> int`

### `check_skills_standard.py`

CI gate for docs/skills-standard.md.

- `def is_test_fixture(path) -> bool` — True for a SKILL.md that belongs to a pack's test fixtures, not discovery.
- `def check_skills(root) -> tuple[list[str], list[str], int, int, int]` — Return (errors, warnings, live, archived, discovery_bytes).
- `def main() -> int`

### `classify_hydrate_state.py`

Classify SessionStart hydrate markdown as degraded or healthy.

- `HydrateVerdict`
- `def classify_verdict(markdown) -> HydrateVerdict` — Full verdict: degraded flag + reason, and the typed non-degraded condition.
- `def classify(markdown) -> tuple[bool, str]` — Return (degraded, reason) for a hydrate markdown block.
- `def main() -> int`

### `claude_bootstrap_receipt.py`

Read the Claude adapter bootstrap receipt and classify it at read time.

- `def schema_for(surface) -> str`
- `def live_governance_revision(root) -> str` — The governance revision this session is actually running.
- `def receipt_path(env) -> Path`
- `def evaluate(receipt) -> dict[str, Any]`
- `def reprobe_degraded(result) -> dict[str, Any]` — Fail-soft: attach a reason and log path per non-READY component.
- `def read(path) -> dict[str, Any]`
- `def main(argv) -> int`

### `claude_projection.py`

The one Claude projection engine.

- `DomainOutcome`
- `def default_receipt_path() -> Path`
- `def governance_sha(root) -> str`
- `def project_skills(root, workspace, check) -> DomainOutcome`
- `def project_commands(root, workspace, check) -> DomainOutcome`
- `def project_rules(root, workspace, check) -> DomainOutcome`
- `def project_settings(root, workspace, check) -> tuple[DomainOutcome, DomainOutcome]`
- `def load_plugins_desired(root) -> dict[str, Any]`
- _+11 more public symbol(s)_

### `claude_projection_snapshot.py`

Snapshot the Claude Code skill-projection surface from repository state.

- `def repo_root(start) -> Path`
- `def snapshot(root) -> dict[str, Any]` — Build the Claude Code projection snapshot for the tree at ``root``.
- `def main(argv) -> int`

### `compose_pr_body.py`

Autonomous PR-body compile for make pr.

- `MechanicalFacts`
- `ComposeResult`
- `def collect_mechanical(workspace) -> MechanicalFacts`
- `def range_problem(facts) -> str` — The Problem statement for the whole range.
- `def range_summary(facts) -> str` — One line: the oldest subject plus the count of what follows.
- `def range_title(facts) -> str` — The PR title: the oldest own subject, no count. Empty when the range is empty
- `def range_fix(facts) -> str` — The Fix: every commit subject, oldest first. One commit reads as one line.
- `def path_why(facts, path) -> str` — Why this path changed: the subject of the commit that last touched it.
- _+5 more public symbol(s)_

_+60 further module(s) in this directory._

## Entrypoints

- `agent_worktree_start.sh`
- `attribute_tree_writers.sh`
- `backup_gate.sh`
- `backup_to_github.sh`
- `bootstrap_agent_environment.sh`
- `check_governance_wiring.sh`
- `classify_generated_dirtiness.sh`
- `clean_pyc.sh`
- `ensure_git_merge_drivers.sh`
- `ensure_gov_python.sh`
- `ensure_uv_environment.sh`
- `ensure_workspace_wired.sh`
- `export_chats.sh`
- `git_merge_driver_generated.sh`
- `governance_activate_fresh.sh`
- `governance_sync.sh`
- `install_commit_hook.sh`
- `install_cursor_hooks_bootstrap.sh`
- `install_export_job.sh`
- `install_ide_profile.sh`
- `install_l9_dispatcher.sh`
- `open_pr_after_gate.sh`
- `pr_preflight.sh`
- `process_context.sh`
- `process_learnings.sh`
- `relocate_plugin_siblings.sh`
- `resolve_changed_files.sh`
- `resolve_governance_paths.sh`
- `run_ff_post_shelf.sh`
- `run_improve.sh`
- `run_pr_gate.sh`
- `run_pr_precommit.sh`
- `run_pr_security.sh`
- `run_pytest_suites.sh`
- `run_rules_stabilization_validation.sh`
- `run_workspace_clean.sh`
- `session_init.sh`
- `setup_claude_code_plugins.sh`
- `setup_workspace_symlinks.sh`
- `show_context.sh`
- `tenx_status.sh`
- `validate_governance_no_hardcoded_paths.sh`
- `validate_governance_symlinks.sh`
- `verify-setup-alignment.sh`
- `verify_docker.sh`
- `wire_governance_workspace.sh`
- `worktree_add_wired.sh`

## Dependencies

**Internal:** `breakglass_receipt`, `claude_bootstrap_receipt`, `dirtiness`, `environment`, `generate_commands_manifest`, `generate_rules_manifest`, `governance_refresh_receipt`, `harvest_worktree_dirt`, `lib`, `prune_open_pr_copies`, `reconcile_claude_l9_skills`, `repo_hygiene`, `safe_https`, `session_authored_ledger`, `sync_generated_artifacts`, `verification_bypass_gate`, `workspace_roots`

**External:** `memory_aggregator`, `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
