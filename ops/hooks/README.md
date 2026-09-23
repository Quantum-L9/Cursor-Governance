# Session hooks

**Path:** `ops/hooks` | **Tier:** operations

## Purpose

Activate governance, hydrate Graphiti, and deny mid-execution publish.

SessionStart bootstrap and shell gates.

## Components

### `Deadline`

One outer budget shared by every child call of a single prefetch.

- File: `ops/hooks/plan_memory_prefetch.py` (L342–352)
- Methods: `remaining`, `budget`

### Shell entrypoints

- `ops/hooks/before-shell-execution-gate.sh`
- `ops/hooks/before_mcp_code_graph_gate.sh`
- `ops/hooks/ensure_graphiti_tunnel.sh`
- `ops/hooks/graphiti-gate-edits.sh`
- `ops/hooks/graphiti-gate-shell.sh`
- `ops/hooks/graphiti-gate-subagent.sh`
- `ops/hooks/graphiti-mark-ok.sh`
- `ops/hooks/graphiti-prefetch.sh`
- `ops/hooks/graphiti-reset-generation.sh`
- `ops/hooks/graphiti-session-end.sh`
- `ops/hooks/graphiti_common.sh`
- `ops/hooks/graphiti_gate_runner.sh`
- `ops/hooks/l4-local-execution-gate-shell.sh`
- `ops/hooks/lifecycle-subagent-start.sh`
- `ops/hooks/lifecycle-subagent-stop.sh`
- `ops/hooks/plan-kernel-execute-gate.sh`
- `ops/hooks/pr_gate_failure_shell.sh`
- `ops/hooks/pre-tool-use-code-graph-gate.sh`
- `ops/hooks/pre_tool_use_code_graph_gate.sh`
- `ops/hooks/session_end_governance_backup.sh`

## Functions

- `def main() -> int`
- `def load_plane() -> types.SimpleNamespace` — Import the shared routing package as ``l9_skill_routing`` from disk.
- `def extract_prompt(payload) -> str`
- `def proactive_enabled() -> bool`
- `def route_event(payload, plane) -> dict[str, Any] | None` — Resolve scope, route, materialize, and persist one receipt state.
- `def main() -> int`
- `def child_conversation_id(payload) -> str`
- `def project_dir(payload) -> str`
- `def main() -> int`
- `def repo_root() -> Path`
- `def plans_store() -> Path | None`
- `def is_store_plan(path) -> bool`
- `def workspace_from_event(event) -> Path`
- `def written_path(event) -> Path | None`
- `def required_path(workspace) -> Path`
- `def write_required(workspace, plan) -> Path`
- `def load_required_plan(workspace) -> Path | None`
- `def plan_fails(path) -> bool`
- `def newest_recent_unbuilt_failing() -> Path | None`
- `def inject_block(workspace) -> str`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `datetime`, `fnmatch`, `importlib`, `importlib.util`, `json`, `os`, `pathlib`, `re`, `session_authored_ledger`, `subprocess`, `sys`, `tempfile`, `time`, `types`, `typing`

<!-- l9-module-readme: generated-from-ast -->
