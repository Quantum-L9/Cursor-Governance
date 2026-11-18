# Claude Code bridge

Root authorization and gating remain `ops/autonomy/`. Claude multi-lane scheduling is not owned by this skill: multi-lane campaign execution is Program Execution's (`make campaign`, `PROGRAM_EXECUTION_REGISTERED_STAGE_V1`), which consumes root autonomy one way. This pack does not invent a Claude scheduler.

1. Root `autonomy/` remains the authorization and control plane.
2. A Claude PreToolUse event reaches the existing root execution gate through `environment/agents/adapters/claude-code/hooks/local_execution_gate_wrap.py`.
3. SessionStart context bootstrap remains fail-open; degraded context does not widen authority.

When the session is Cursor Composer/Agent, use the same root autonomy gate. No surface may invent a second scheduler.
