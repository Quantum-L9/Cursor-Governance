# Session hooks

**Path:** `ops/hooks` | **Kind:** subsystem

## Purpose

Activate governance, hydrate Graphiti, and deny mid-execution publish.

## Description

SessionStart bootstrap and shell gates.

## Modules

### `before_shell_execution_gate.py`

One beforeShellExecution process: Graphiti shell + L4 + plan-kernel.

- `def main() -> int`

### `before_submit_skill_router.py`

Cursor beforeSubmitPrompt adapter for the L9 Virtual Skill Plane.

- `def load_plane() -> types.SimpleNamespace` — Import the shared routing package as ``l9_skill_routing`` from disk.
- `def extract_prompt(payload) -> str`
- `def proactive_enabled() -> bool`
- `def route_event(payload, plane) -> dict[str, Any] | None` — Resolve scope, route, materialize, and persist one receipt state.
- `def main() -> int`

### `plan_kernel_gate.py`

Plan kernel-pass hook: postToolUse latch + execute deny + inject prefix.

- `def repo_root() -> Path`
- `def plans_store() -> Path | None`
- `def is_store_plan(path) -> bool`
- `def workspace_from_event(event) -> Path`
- `def written_path(event) -> Path | None`
- `def required_path(workspace) -> Path`
- `def write_required(workspace, plan) -> Path`
- `def load_required_plan(workspace) -> Path | None`
- _+10 more public symbol(s)_

### `plan_memory_prefetch.py`

Hydrate memory before either planning skill drafts.

- `Deadline` — One outer budget shared by every child call of a single prefetch.
- `def extract_prompt(payload) -> str`
- `def route_skill_names(receipt) -> set[str]`
- `def load_route_receipt(payload) -> dict[str, Any] | None` — Best-effort read of the conversation route written by the skill router.
- `def planning_requested(payload) -> bool`
- `def conflicts_cite(document) -> dict[str, Any]` — GMP Phase 0 MEMORY_PREFETCH fields — never episode names.
- `def hydrate_state(document, returncode) -> str` — HIT / NO_HIT / DEGRADED from a canonical hydrate receipt.
- `def conflicts_state(cite, returncode) -> str` — CONFLICT only when the authoritative service reports conflict evidence.
- _+7 more public symbol(s)_

### `pr_publish_memory_write.py`

Last-step ``make pr`` memory handoff (operator CLI write).

- `def summary_identity_check(summary, current) -> tuple[bool, list[str], list[str]]` — Bind a cached summary to the current publication before trusting it.
- `def format_fact(summary) -> str | None` — One terse resume fact. Empty only when there is no PR identity.
- `def idempotency_key(summary, fallback) -> str`
- `def write_argv() -> list[str]`
- `def run_write(argv) -> subprocess.CompletedProcess[str]`
- `def main(argv) -> int`

### `session_authored_paths.py`

postToolUse + afterShellExecution: record paths this conversation authored.

- `def main() -> int`

### `workspace_open_plugin_loader.py`

Cursor workspaceOpen hook: per-workspace-class addon plugin loader.

- `def resolve_governance_root() -> Path | None` — SSOT: the local GitHub clone at $HOME/.cursor-governance, and only that.
- `def load_yaml_dict(path) -> dict[str, Any]`
- `def load_json_dict(path) -> dict[str, Any]`
- `def has_marker(workspace, pattern, max_depth) -> bool` — True if a file/dir matching `pattern` (glob or literal) exists within
- `def classify_workspace(workspace, exceptions) -> str` — First-match-wins classification: odoo_plasticos -> aws_infra ->
- `def addon_plugin_paths_for_class(class_name, gov_root, policy, render) -> list[str]`
- `def compute_plugin_paths(workspace_roots) -> list[str]`
- `def classify_only(workspace_arg) -> int` — `--classify <path>` mode: print just the class name for one workspace.
- _+1 more public symbol(s)_

## Entrypoints

- `before-shell-execution-gate.sh`
- `before_mcp_code_graph_gate.sh`
- `ensure_graphiti_tunnel.sh`
- `graphiti-gate-edits.sh`
- `graphiti-gate-shell.sh`
- `graphiti-gate-subagent.sh`
- `graphiti-mark-ok.sh`
- `graphiti-prefetch.sh`
- `graphiti-reset-generation.sh`
- `graphiti-session-end.sh`
- `graphiti_common.sh`
- `graphiti_gate_runner.sh`
- `l4-local-execution-gate-shell.sh`
- `lifecycle-subagent-start.sh`
- `lifecycle-subagent-stop.sh`
- `plan-kernel-execute-gate.sh`
- `pr_gate_failure_shell.sh`
- `pre-tool-use-code-graph-gate.sh`
- `pre_tool_use_code_graph_gate.sh`
- `session_end_governance_backup.sh`
- `session_end_repo_hygiene.sh`
- `session_start_bootstrap.sh`
- `session_start_code_graph_health.sh`
- `session_start_memory_orchestrator.sh`

## Dependencies

**Internal:** `session_authored_ledger`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
