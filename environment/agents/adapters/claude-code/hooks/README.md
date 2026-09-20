# Hooks

**Path:** `environment/agents/adapters/claude-code/hooks` | **Kind:** subsystem

## Modules

### `context7_stack_pretool.py`

Deny first Edit/Write of stack files unless Context7 ran or a PASS receipt exists.

- `def main() -> int`

### `local_execution_gate_wrap.py`

Claude PreToolUse wrapper: Program-bound root authorization → ops gate (§2.1).

- `def autonomy_required() -> bool`
- `def authority_from_environment() -> dict[str, Any] | None` — The worker window's root authority, or None when it is incomplete.
- `def persisted_authority(environment_authority) -> tuple[dict[str, Any] | None, str]` — Resolve the window's environment to the grant receipt PE persisted.
- `def authorize(raw) -> int` — 0 when this effect may proceed to the ops gate, 2 when it may not.
- `def main() -> int`

### `memory_gate.py`

PreToolUse memory gate — canonical memory hydration only (stage C8).

- `def main() -> int`

### `memory_prefetch.py`

SessionStart prefetch — thin wrap of the canonical session hydration (stage C8).

- `def prefetch_agent_id(env) -> str` — Writer id for this prefetch run.
- `def hook_session_start_payload(context) -> dict[str, object]` — SessionStart envelope.
- `def main() -> int`

### `memory_writeback.py`

Stop-hook write-back — thin wrap of the canonical session close (stage C8).

- `def main() -> int`

### `merge_gate_wrap.py`

Thin Claude PreToolUse wrapper → ops/autonomy/merge_gate.py (§2.1).

- `def main() -> int`

### `pr_summary_posttool.py`

Put what a publish shipped in front of the model, once, after `make pr`.

- `def render(summary) -> str`
- `def main() -> int`

### `root_file_advisory_wrap.py`

Thin Claude UserPromptSubmit wrapper → ops/autonomy/root_file_advisory.py (§2.1).

- `def main() -> int`

### `session_debt_wrap.py`

Thin Claude Stop hook wrapper → ops/autonomy/session_debt.py (§2.1).

- `def session_roots(stdin_text, environ) -> list[str]` — The repositories this session owns: CLAUDE_PROJECT_DIR and the hook event cwd.
- `def main() -> int`

### `skill_usage_logger.py`

Record metadata-only Claude skill invocations without storing prompt text.

- `def skill_from_payload(payload) -> tuple[str, str]`
- `def main() -> int`

### `user_prompt_skill_router.py`

Claude Code UserPromptSubmit adapter for the L9 skill router.

- `def load_routing(root)`
- `def find_governance_root() -> Path`
- `def log_recommendation(payload, recommendation) -> None`
- `def main() -> int`

## Entrypoints

- `bootstrap_capability_preflight.sh`
- `l9_hook_exec.sh`
- `session_deps_cloud.sh`
- `session_start_claude_governance.sh`

## Dependencies

**Internal:** `classify_hydrate_state`, `memory_bridge`, `memory_state`, `surface_detect`, `workspace_roots`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
