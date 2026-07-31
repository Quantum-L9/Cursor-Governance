<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/codex/setup.md
layer: adapter
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-31
/L9_META -->

# Codex setup (deploy-ready)

Thicker peer of Claude Code's `web/setup.sh` + env pack — Codex has no single
sandbox setup script, so these are the exact operator steps.

## Prerequisites

1. Memory live: `https://memory.quantumaipartners.com/healthz` → 200
2. Token issued for `codex` in `~/.config/l9-memory/agent_tokens.local.json`
3. Principals rendered and synced to C1 (`docs/DEPLOY.md`)
4. Network allowlist includes `memory.quantumaipartners.com` (`docs/network-allowlist.md`)

## Cloud environment

1. Paste `environment.env.example` into the Codex environment variables
   (replace `REPLACE_WITH_MEMORY_CLIENT_BEARER_TOKEN` with the codex token).
2. Register MCP from `mcp.template.json` (URL + Bearer header).
3. Ensure governed repos Codex opens contain the `agents-block.md` section in
   `AGENTS.md` (or paste it once into project instructions).

## CLI (`~/.codex/config.toml`)

1. Export the same env vars in the shell that launches Codex.
2. Merge `config.toml.example` into `~/.codex/config.toml`.
3. Same `AGENTS.md` block as cloud.

## Verify

- Unauthenticated MCP → 401
- Authed session can search/write memory
- Episodes show `user_id=codex_agent`, never `cursor_agent`
