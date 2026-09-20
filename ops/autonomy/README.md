# Autonomy plane

**Path:** `ops/autonomy` | **Kind:** subsystem

## Purpose

Enforce local-commit vs publish vs merge authority without a second scheduler.

## Description

Shared autonomy surface — L4 local gate, merge gate, and profile.

## Modules

### `__init__.py`

Shared autonomy surface contracts (Profile + merge gate + L4 local gate).

### `acceptance_dry_run.py`

Structural acceptance dry-run for Autonomy Surface Parity (no remote PR).

- `def step(name, ok, detail) -> None`
- `def main() -> int`

### `authorize_merge.py`

Write merge authorization for ordinary gh pr merge.

- `def auth_path(explicit) -> Path`
- `def write_authorization() -> dict[str, Any]`
- `def main() -> int`

### `breakglass_receipt.py`

Scoped, expiring publish-path breakglass receipt.

- `def default_receipt_path() -> Path`
- `def load_receipt(path) -> dict[str, Any] | None`
- `def evaluate(receipt) -> dict[str, Any]` — Classify a receipt. Never raises.
- `def active_publish_path_reason() -> str` — Return the grant reason only when a valid unexpired receipt is in force.
- `def write_receipt() -> Path`
- `def status_line() -> str`
- `def main(argv) -> int`

### `command_parse.py`

Quote-aware Bash command-string parsing shared by the autonomy gates.

- `def strip_heredoc_bodies(command) -> str` — Remove heredoc bodies; keeps the line that opens the heredoc.
- `def split_segments(command) -> list[str]` — Split on ``&&`` ``||`` ``;`` ``|`` newline, honoring single/double quotes.
- `def segment_words(segment) -> list[str]` — Word-split a segment honoring quotes (no glob/expansion semantics).
- `def segment_head(segment) -> str | None` — First command word of a segment, skipping env-assignment prefixes.
- `def wrapper_subcommands(segment) -> list[str]` — Nested command strings carried by wrapper invocations (``bash -c '…'``).
- `def make_workspace_raw(segment) -> str | None` — Last ``WS=`` / ``L9_L4_WORKSPACE=`` on a make segment, or None.
- `def extract_named_roots(command) -> list[str]` — Static repo paths named by ``git -C``, make ``WS=`` / ``make -C``, or ``cd``.

### `execution_profile.py`

Resolve the execution personality of the current session.

- `def governance_root() -> Path`
- `def load_policy(root) -> dict[str, Any]`
- `def classify(env, policy) -> str` — Resolve execution personality from canonical surface identity plus Claude policy.
- `def resolve_provider(env, policy) -> str`
- `def worker_target(provider, policy, root) -> tuple[int | None, str]` — Worker slots for this provider, and where the number came from.
- `def settings_candidates(workspace, home) -> list[Path]` — Settings files in Claude Code precedence order (most specific first).
- `def read_setting(key, workspace, home) -> tuple[Any, str | None]`
- `def declared_env_int(name, workspace, home) -> int | None` — Read an `env` sub-key from the scopes that DECLARE configuration.
- _+3 more public symbol(s)_

### `first_publication_gate.py`

Publication plane: a *first* publication happens only through ``make pr``.

- `def breakglass_reason() -> str | None` — Human/ops authorization that waives this plane, or None.
- `def publication_forms(command, root) -> list[dict[str, Any]]` — Every publication a command would perform, in order.
- `def first_publication_verdict(command) -> str | None` — Deny reason when ``command`` performs a first publication, else None.

Exports: `PUSH_BREAKGLASS_ENV`, `breakglass_reason`, `first_publication_verdict`, `publication_forms`

### `git_execution_exemption.py`

Workflow-plane execution exemption for ``git`` and ``gh`` shell commands.

- `def command_is_git_or_gh(command) -> bool` — True when every command in ``command`` is git/gh (and at least one is).
- `def command_from_input(tool_input) -> str`
- `def event_is_git_or_gh(tool_name, tool_input) -> bool` — True for a shell tool invocation whose command is git/gh only.
- `def payload_is_git_or_gh(raw) -> bool` — Best-effort check straight off a raw hook payload. Never raises.

### `git_guardrails.py`

Context-sensitive git / filesystem guardrails.

- `Outcome` — Contract ``execution_outcomes``, ordered least → most restrictive.
- `Effect` — Contract ``risk_dimensions.effect``.
- `Sensitivity` — Contract ``risk_dimensions.sensitivity``.
- `Recoverability` — Contract ``risk_dimensions.recoverability``.
- `BlastRadius` — Contract ``risk_dimensions.blast_radius``.
- `Purpose` — Why the agent is running the operation (contract ``diagnostic_policy``).
- `Ownership` — Contract ``ownership`` — who a changed path belongs to.
- `Finding` — One classified effect of one command segment.
- _+19 more public symbol(s)_

Exports: `BlastRadius`, `CONTRACT_ID`, `CONTRACT_VERSION`, `Decision`, `DirtyPath`, `Effect`, `Finding`, `GuardContext`, `GuardResult`, `HUMAN_AUTHORIZATION_ENV`, `LiveProbe`, `Outcome` (+17 more)

### `kernel_gate.py`

Kernel hook that fires before pre-commit hooks and tests.

- `ReceiptLoadError` — An existing kernel receipt could not be read as a JSON object.
- `def adapter_tree_kernels_required(environ) -> bool` — Compat alias of ``kernel_latch_required`` (adapter ``make pr`` only).
- `def changed_are_corpus_only(changed_paths) -> bool`
- `def gov_root_from_env(explicit) -> Path`
- `def workspace_root(explicit) -> Path`
- `def receipt_path(root) -> Path`
- `def kernel_shas(gov) -> dict[str, str]`
- `def load_receipt(root) -> dict[str, Any] | None` — Load the kernel receipt, or None when no file exists.
- _+18 more public symbol(s)_

### `kernel_predicates.py`

Cheap structural predicates for the tree-kernel apply report.

- `ReportError` — Apply-report contract failure.
- `def confine_report_path(root, report) -> Path` — Resolve report and refuse any path that leaves workspace/.l9/autonomy/.
- `def parse_apply_report(path) -> dict[str, Any]`
- `def report_structure(root, report) -> list[str]`
- `def delta_paths_exist(root, deltas) -> list[str]`
- `def report_sha(path, expected) -> list[str]`
- `def load_validated_deltas(root, report) -> list[dict[str, str]]`
- `def run_predicates(root, receipt) -> list[str]` — Re-run the three structural predicates against live files.

Exports: `APPLY_REL`, `APPLY_SCHEMA`, `ReportError`, `confine_report_path`, `delta_paths_exist`, `load_validated_deltas`, `report_sha`, `report_structure`, `run_predicates`, `sha256_file`

### `l4_local.py`

L4 local autonomy — stacked local commits, no mid-execution push.

- `def workspace_root(explicit) -> Path`
- `def workspace_from_event(event) -> Path` — Resolve workspace from a Claude/Cursor hook event, else cwd git root.
- `def workspace_identity(root) -> str` — Stable identity of the workspace an L4 state file belongs to.
- `def state_path(root) -> Path`
- `def receipt_path(root) -> Path`
- `def breakglass_path(root) -> Path`
- `def current_branch(root) -> str` — The checked-out branch, including on a repository with no commits.
- `def current_head(root) -> str` — The HEAD sha, or "" when HEAD is unborn or unreadable.
- _+22 more public symbol(s)_

_+15 further module(s) in this directory._

## Dependencies

**Internal:** `command_parse`, `execution_profile`, `first_publication_gate`, `git_execution_exemption`, `git_guardrails`, `l4_local`, `merge_gate`, `ops`, `surface_detect`, `sync_generated_artifacts`, `verification_bypass_gate`, `worktree_isolation_gate`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
