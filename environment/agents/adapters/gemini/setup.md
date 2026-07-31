<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/gemini/setup.md
layer: adapter
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-31
/L9_META -->

# Gemini CLI setup (deploy-ready)

## Prerequisites

1. `https://memory.quantumaipartners.com/healthz` → 200
2. Token for `gemini` in `agent_tokens.local.json`; principals on C1
3. Gemini CLI installed; shell can reach the memory host

## Steps

1. Export vars from `environment.env.example` (replace the bearer placeholder).
2. Merge `settings.template.json` → `~/.gemini/settings.json` (`mcpServers`).
3. Append `gemini-block.md` into each governed repo's `GEMINI.md` (or project
   context file Gemini reads).
4. Role is **reviewer**: server grants write only to `<group>.reviews`.

## Verify

- MCP tools load with Bearer auth
- Writes outside `<group>.reviews` are rejected
- Attribution: `user_id=gemini_agent` / `source=gemini`
