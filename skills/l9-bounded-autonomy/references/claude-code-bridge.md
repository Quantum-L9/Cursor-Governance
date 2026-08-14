# Claude Code bridge

When `L9_GOVERNANCE_SURFACE=claude-code` or the session is clearly Claude Code
CLI/Web/Mobile, use the shared Peer Execution bounded runtime. Claude is a thin
provider and does not own a scheduler.

```bash
python3 "$HOME/.cursor-governance/environment/program-execution/peer_execution/autonomy/cli.py" init <campaign.json>
python3 "$HOME/.cursor-governance/environment/program-execution/peer_execution/autonomy/cli.py" plan <campaign-id>
```

1. Shared bounded-runtime default profile:
   `environment/program-execution/peer_execution/autonomy/profiles/pr-convergence.json`.
2. Root `autonomy/` remains the authorization/control plane and owns no Program state.
3. Peer Execution Core owns admitted-dispatch concurrency and lifecycle mechanics.
4. Claude-specific code owns only Claude invocation and response translation.
5. SessionStart context bootstrap remains fail-open; degraded context does not widen authority.

When the session is Cursor Composer/Agent, use the same Program Controller and
Peer Execution substrate through the Cursor provider binding. No surface may
invent a second scheduler.
