<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/ADAPTER_CONTRACT.md
layer: contract
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-31
/L9_META -->

# Adapter contract (from Claude Code gold standard)

Every surface under `environment/agents/adapters/<name>/` must provide the
**same three carriers** that `environment/claude-code/` already ships. Claude
Code itself stays at `environment/claude-code/` (preexisting peer of
`environment/ide/`); this contract is how the thinner adapters catch up.

| Need | Claude Code carrier | Required in each agents adapter |
|---|---|---|
| **Discover governance** | clone + `.claude/` triad / skills | README setup step that clones or points at `Quantum-L9/Cursor-Governance` |
| **Boot context** | SessionStart hook / bootstrap | `session_bootstrap.md` **or** `agents-block.md` **or** `gemini-block.md` **or** `bootstrap.template.md` |
| **Reach shared memory** | `mcp.template.json` + account env | One of: `mcp.template.json`, `mcp-connector.json`, `settings.template.json`, `config.toml.example` |
| **Identity env** | `web/environment.env.example` | `environment.env.example` with registry-matching `USER_ID` / `L9_MEMORY_AGENT_ID` / `L9_MEMORY_SOURCE` |
| **Network** | `web/network-policy.md` | Point at `docs/network-allowlist.md` (shared) |

## Memory endpoint (binding)

Production control plane (non-secret):

```text
https://memory.quantumaipartners.com
```

MCP path: `/mcp`. Auth: `Authorization: Bearer ${L9_MEMORY_CLIENT_TOKEN}`.
Each agent uses **its own** token (`L9_MEMORY_TOKEN__<AGENT>` issued into
`~/.config/l9-memory/agent_tokens.local.json`, rendered into server
`auth_tokens.json`). Never share tokens across agents. Never commit tokens.

Env examples MUST set:

```bash
L9_MEMORY_HTTP_URL=https://memory.quantumaipartners.com
L9_MEMORY_CLIENT_TOKEN=REPLACE_WITH_MEMORY_CLIENT_BEARER_TOKEN
```

(or an obvious `REPLACE` / `<angle>` placeholder for the token). Loopback
URLs are local-only and **must not** be the default in any adapter MCP
carrier or env example.

## Identity (binding)

Values come only from `agent_registry.yaml`. Adapters never invent a second
`agent_id`. Writing identity is distinct from Cursor's `cursor_agent`.
`group_id` stays shared (repo namespace from `ops/graphiti/group_registry.yaml`).

## Validator

`tools/validate_agents.py` enforces this contract for every **active** agent
whose `adapter` is not `cursor` or `claude-code`. Run `make agents-env`.
