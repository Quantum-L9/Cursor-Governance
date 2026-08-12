# Claude Code bridge

When `L9_GOVERNANCE_SURFACE=claude-code` (or the session is clearly Claude Code CLI/Web/Mobile):

1. **Do not invent a second scheduler.** Use the shipped runtime:

```bash
python3 "$HOME/.cursor-governance/environment/agents/adapters/claude-code/autonomy/cli.py" init <campaign.json>
python3 "$HOME/.cursor-governance/environment/agents/adapters/claude-code/autonomy/cli.py" plan <campaign-id>
```

2. Profile default: `environment/agents/adapters/claude-code/autonomy/profiles/pr-convergence.json`.
3. Permissions and env already encode A4 remediation + merge OFF — see `settings.template.json`.
4. This Cursor skill remains the **SOP narrative** and cross-surface contract; Claude machine enforcement stays in `autonomy/*.py` + permissions.
5. SessionStart autonomy bootstrap is fail-open — degraded context must not block startup.

When the session is Cursor Composer/Agent: follow Protocols A–C with Task tools; do not require `cli.py` unless the user asks to drive a Claude campaign from the same repo.
