<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/generic/README.md
layer: adapter
owner: governance-control-plane
status: active
version: 1.1.0
updated: 2026-07-31
/L9_META -->

# Generic Adapter — any future MCP-capable LLM surface

Use this to onboard a surface that has no dedicated adapter yet (Windsurf,
VS Code Copilot, open-source CLIs, custom bots). Follow
`../ADAPTER_CONTRACT.md` — the same three carriers as Claude Code.

Claude Code stays at `environment/claude-code/`; do not relocate it here.

## 1. Register the agent (identity first)

Add an entry to `../../agent_registry.yaml` following the naming law
(`agent_id` kebab-case; `user_id=<agent_id>_agent`; `source=agent_id`;
`principal_id=<agent_id>-memory-client`; `token_env=L9_MEMORY_TOKEN__<AGENT>`;
pick a role; list `assigned_groups`; `status: active`). Run
`tools/validate_agents.py` — it must pass before anything else.

## 2. Issue the principal

Add `"<agent_id>": "<fresh ≥24-char token>"` to `agent_tokens.local.json`,
run `tools/render_principals.py`, sync to C1 per `docs/DEPLOY.md`.

## 3. Create `adapters/<agent_id>/` from this template

Copy and fill:

| From generic | Required in named adapter |
|---|---|
| `environment.env.example` | Identity lines matching registry; `L9_MEMORY_HTTP_URL=https://memory.quantumaipartners.com` |
| `mcp.template.json` | Replace `${AGENT_ID}` with the real agent_id |
| `bootstrap.template.md` | Fill `{{AGENT_ID}}` / `{{ROLE}}` → rename to `session_bootstrap.md` |
| README | Setup + role limits |

## 4. Wire the surface

```bash
L9_MEMORY_HTTP_URL=https://memory.quantumaipartners.com
L9_MEMORY_CLIENT_TOKEN=<its own token>
USER_ID=<agent_id>_agent
L9_MEMORY_AGENT_ID=<agent_id>
L9_MEMORY_SOURCE=<agent_id>
```

Point its MCP client at `/mcp` with Bearer auth. Inject the bootstrap into
its system-prompt/instructions carrier. Allowlist
`memory.quantumaipartners.com` (`docs/network-allowlist.md`).
