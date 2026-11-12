---
# Hand-maintained since 2026-11-12: the SessionStart binding section below is written by
# hand, so the README generator must not overwrite this file.
auto_generated: false
---
# Session hooks

**Path:** `ops/hooks` | **Tier:** operations

## Purpose

Activate governance, hydrate Graphiti, and deny mid-execution publish.

SessionStart bootstrap and shell gates.

## SessionStart projection binding (how it works)

`session_start_bootstrap.sh` is Cursor's SessionStart hook (installed as
`~/.cursor/hooks/session-start-bootstrap.sh`). It binds every Cursor session to its
default projections; no skill or command is involved.

- `governance/host-bindings/cursor.yaml` holds the binding: the operating plane
  (`l9.projection/cursor-governance-operating-plane@2`) as the required base, plus the
  canonical Cursor domain set.
- The hook runs `ops/autonomy/host_binding.py --host cursor --format markdown`, which
  checks the binding with the verifiers that already exist and adds no checking of its
  own.
  - It reports `BOUND` only when the operating plane is current and every active
    projection is admitted and current; `DEGRADED` when the operating plane is bound and
    some active domain is not (what verified stays bound); `NOT BOUND` when the operating
    plane did not verify (nothing is bound).
  - A conditional projection is loaded only when its condition is named with
    `--activate`; otherwise it isn't even checked. SessionStart names none, so only the
    `always` domains are checked there.
- The report appears as `### default projection binding (cursor)`, after the
  `### coding projection` block. It replaced the old report-only operating-plane block,
  so the operating plane is checked once, not twice. 30 s limit inside the 60 s hook; it
  took about 9 s in testing against an authority checkout at `main`.
- Fail-open and honest: a binding that failed, degraded or timed out never stops the
  session, and the block says exactly what is and is not bound. Its fallbacks read
  `NOT BOUND — host binding unavailable` / `TIMED OUT after 30 s ... (fail-open: the
  session continues; cite no operating-plane semantics)`.
- The `### coding projection` block is verification only and says so: the coding-agent
  execution projection is bound by `/coding-agent`, not here.

Claude Code does the same from
`environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh`
(`--host claude-code --format line`). Full detail: `governance/host-bindings/README.md`.

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
