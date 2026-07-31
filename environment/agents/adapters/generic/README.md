<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/generic/README.md
layer: adapter
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-28
/L9_META -->

# Generic Adapter — any future MCP-capable LLM surface

Use this to onboard a surface that has no dedicated adapter yet (Windsurf,
VS Code Copilot, open-source CLIs, custom bots). Three steps, no exceptions:

## 1. Register the agent (identity first, always)

Add an entry to `../../agent_registry.yaml` following the naming law
(`agent_id` kebab-case; `user_id=<agent_id>_agent`; `source=agent_id`;
`principal_id=<agent_id>-memory-client`; `token_env=L9_MEMORY_TOKEN__<AGENT>`;
pick a role from the catalog; list `assigned_groups`). Run
`tools/validate_agents.py` — it must pass before anything else happens.

## 2. Issue the principal

Add `"<agent_id>": "<fresh ≥24-char token>"` to `agent_tokens.local.json`
(gitignored) on the render host, run `tools/render_principals.py`, restart the
memory server. The agent now authenticates as exactly one principal with
role-derived namespace grants.

## 3. Wire the surface

Set the four identity envs + endpoint in whatever carrier the surface offers
(account env, settings file, container env):

```bash
L9_MEMORY_HTTP_URL=https://<memory-host>
L9_MEMORY_CLIENT_TOKEN=<its own token>
USER_ID=<agent_id>_agent
L9_MEMORY_AGENT_ID=<agent_id>
L9_MEMORY_SOURCE=<agent_id>
```

Point its MCP client at the shared server using `mcp.template.json`, and
inject `bootstrap.template.md` (fill the placeholders from the registry entry)
into its system-prompt/instructions carrier.

That is the entire onboarding surface area: one registry entry, one token,
one env block, one bootstrap. Everything else derives.
