# Claude Agent SDK adapter (L9)

Third governed surface after Cursor and Claude Code CLI/Web. Consumes the **same** committed
governance artifacts and the **same** hook launcher; introduces no new SSOT.

| Concern | Mechanism |
|---|---|
| Load governance | `setting_sources=["project"]` -> `CLAUDE.md`, `.claude/settings.json`, `.mcp.json` |
| Hook dispatch | `l9_dispatch` -> `$HOME/.cursor-governance/environment/agents/adapters/claude-code/hooks/l9_hook_exec.sh --class {governor|observer}`; no-op if launcher absent (matches `.claude/settings.json`) |
| Hard denies | `config.yaml` `disallowed_tools` (each mapped to an invariant); apply in every permission mode |
| SSOT protection | In-process `invariant_guard` on Write/Edit/MultiEdit for `protected_files` / `protected_prefixes` |
| Subagents | `l9-auditor` (Read/Grep/Glob only), `l9-remediator` |
| Output | JSON report (`reports/agent_sdk/latest.json`) + append-only `telemetry/agent_sdk_audit.jsonl` |
| Spend | `max_budget_usd`, `max_turns`, file checkpointing for rewind |

## Install

```bash
uv add claude-agent-sdk          # Python >= 3.10; bundles the Claude Code CLI
export ANTHROPIC_API_KEY=sk-ant-...
python environment/agents/adapters/claude-agent-sdk/validate_agent_sdk_env.py
```

## Run

```bash
A=environment/agents/adapters/claude-agent-sdk/l9_agent.py
uv run $A                                   # read-only audit, default permissions
uv run $A --mode plan                       # plan-only, no mutations
uv run $A "Fix top findings with l9-remediator" --mode acceptEdits --budget 5
```

## Tests

```bash
pytest -q environment/agents/adapters/claude-agent-sdk/tests
```

## Open items

- Confirm `governor_veto_exit_code` matches `l9_hook_exec.sh`; only `--class observer` is exercised by the committed `.claude/settings.json`.
- Makefile targets (`agent-sdk`, `agent-sdk-plan`, `agent-sdk-validate`) and `pyproject.toml` dependency to be added in the stacked follow-up.
- `AGENTS.md` / `CLAUDE.md` surface table rows via `l9-update-agent-docs`.
