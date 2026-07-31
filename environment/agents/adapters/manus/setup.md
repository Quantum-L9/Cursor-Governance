<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/manus/setup.md
layer: adapter
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-31
/L9_META -->

# Manus setup (deploy-ready)

Manus maps onto Claude Code's three carriers (skills / bootstrap / HTTP MCP)
using Manus-native persistence. See `README.md` for the carrier table.

## Prerequisites

1. `https://memory.quantumaipartners.com/healthz` → 200
2. Token for `manus` rendered into C1 `auth_tokens.json` (`docs/DEPLOY.md`)
3. Allowlist: `memory.quantumaipartners.com` (`docs/network-allowlist.md`)

## Steps

1. Create Custom MCP connector from `mcp-connector.json`:
   - URL: `https://memory.quantumaipartners.com/mcp`
   - Header: `Authorization: Bearer <manus token>`
2. Paste `environment.env.example` into the connector/session env (token
   placeholder → real manus bearer only).
3. Paste `session_bootstrap.md` into project instructions or a Manus skill so
   every task boots with identity + work-claim rules.
4. Confirm GitHub integration can clone `Quantum-L9/Cursor-Governance`.

## Verify

- Connector tools list succeeds with Bearer; fails without
- Claims/writes attribute to `manus_agent` / `manus`
- No impersonation of `cursor_agent` or `claude_code_agent`
