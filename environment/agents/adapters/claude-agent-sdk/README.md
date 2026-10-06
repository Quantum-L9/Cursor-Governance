# Claude Agent SDK adapter

A thin Cursor-Governance runtime harness that drives the existing Claude Code
actor through the Claude Agent SDK. It is **not** a new L9 ProductKind or
SurfaceIdentity, and it introduces no governance of its own: it consumes the
project governance Claude Code already loads.

| Concern | Owner |
|---|---|
| Instructions | `CLAUDE.md` (loaded via `setting_sources=["project"]`) |
| Permissions and hooks | `.claude/settings.json` — the same file Claude Code reads |
| External MCP servers | `.mcp.json` — project-owned; the SDK adds none |
| Runtime mechanics | `l9_agent.py`: cwd, permission mode, `max_turns`, `max_budget_usd`, JSON-schema report, file checkpointing, MCP status, SDK error handling |
| Adapter obligations | `validate_agent_sdk_env.py` |

`l9_agent.py` passes no `allowed_tools`, `disallowed_tools`, `hooks`,
`agents`, `can_use_tool`, `mcp_servers` or appended system prompt. The
validator and tests fail if one is added.

## Install

The SDK is a locked optional extra (each platform wheel bundles the Claude Code
CLI, ~100 MB, so it is not in the default governance environment):

```bash
uv sync --locked --extra dev --extra agent-sdk   # Python >= 3.12 (repo baseline)
python environment/agents/adapters/claude-agent-sdk/validate_agent_sdk_env.py
```

The validator prints `PASS` (exit 0), `FAIL` (exit 1, an obligation is broken),
or `UNKNOWN` (exit 3, nothing broken but something undeterminable — typically
the extra is not synced in this interpreter).

## Run

```bash
A=environment/agents/adapters/claude-agent-sdk/l9_agent.py
uv run --extra agent-sdk python $A --mcp-status                 # project MCP status; no API key
uv run --extra agent-sdk python $A "Summarize open plan shelves" --mode plan
uv run --extra agent-sdk python $A "<task>" --mode acceptEdits --budget 5 --turns 20
```

A task run needs `ANTHROPIC_API_KEY`. The report is written to
`reports/agent_sdk/latest.json` (gitignored): the model's structured output
plus result metadata and per-server MCP `name` / `status` / `scope` / `error`
(server `config` is omitted because it can carry environment values).

## Workspace trust

The Claude Code CLI ignores `permissions.allow` from `.claude/settings.json`
until the workspace is trusted (`hasTrustDialogAccepted` in the host's
`~/.claude.json`). Untrusted, a non-interactive SDK run fails closed: tools the
project would allow are denied. Trust the workspace on the host; do not add an
adapter-side allowlist to compensate.

## Tests

```bash
pytest -q environment/agents/adapters/claude-agent-sdk/tests
```

One test exercises the real `claude_agent_sdk` types and runs only where the
`agent-sdk` extra is synced; the rest need neither the SDK nor network.
