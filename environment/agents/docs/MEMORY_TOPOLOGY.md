<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/docs/MEMORY_TOPOLOGY.md
layer: doc
owner: governance-control-plane
status: active
version: 1.1.0
updated: 2026-07-31
/L9_META -->

# Memory Topology — one server, N surfaces

## 1. The requirement

All agents write to the **same** memory graph via one long-running HTTPS
control plane (`https://memory.quantumaipartners.com`) and per-agent bearer
tokens. Cursor IDE may still use the separate Graphiti SSH tunnel (`:8100`);
that path does not reach cloud sandboxes — adapters must default to the
HTTPS URL, never loopback.

## 2. Live deployment (Option A — ACTIVE)

| Item | Value |
|---|---|
| Public URL | `https://memory.quantumaipartners.com` |
| MCP | `https://memory.quantumaipartners.com/mcp` |
| Origin | C1 `46.62.243.82` — Caddy TLS → `127.0.0.1:8200` |
| Process | systemd `l9-memory-server` under `/opt/l9-memory` |
| Package | `l9-graphite-memory[server]` |
| Auth | `auth_tokens.json` from `tools/render_principals.py` |

Registry field: `memory.production_url` in `agent_registry.yaml`.

| Option | What runs where | Reaches cloud agents? | Status |
|---|---|---|---|
| **A. C1 HTTPS** | control plane behind Caddy | **Yes** | **LIVE** |
| B. Tunnel-only Graphiti | Cursor SSH tunnel `localhost:8100` | No | Cursor-local legacy path (still valid for Cursor IDE) |
| C. Per-host loopback `:8200` | one server per host | No | Local-only |

## 3. Operator wiring

See `DEPLOY.md` for the full checklist (validate → render principals → sync to
C1 → wire each adapter). Short form:

```bash
python3 environment/agents/tools/render_principals.py \
  --root     environment/agents \
  --out-dir  ~/.config/l9-memory \
  --registry agent_registry.yaml \
  --tokens   agent_tokens.local.json \
  --out      auth_tokens.json
# Then sync auth_tokens.json to C1 /opt/l9-memory/config/ and restart
# l9-memory-server — only after explicit human approval (VPS rule).
```

Every surface sets:

```bash
L9_MEMORY_HTTP_URL=https://memory.quantumaipartners.com
L9_MEMORY_CLIENT_TOKEN=<that agent's own bearer>
USER_ID=<registry user_id>
L9_MEMORY_AGENT_ID=<registry agent_id>
L9_MEMORY_SOURCE=<registry source>
```

## 4. Non-negotiables

`http_auth_required` stays `true` on any routable bind. One bearer token per
agent, never shared. Graphiti/Neo4j projection for Cursor (`:8100` tunnel)
remains; cloud agents use the HTTPS control plane. `group_id` resolution is
unchanged (`ops/graphiti/group_registry.yaml`).

## 5. Two planes (do not conflate)

| Plane | Reach | Used by |
|---|---|---|
| Graphiti MCP (Cursor) | SSH tunnel `127.0.0.1:8100` | Cursor IDE / `graphiti_memory_client.py` |
| L9 memory HTTP control plane | `https://memory.quantumaipartners.com` | Claude Code Web/Mobile, Manus, Codex, Gemini, generic |

Cursor may later also consume the HTTPS plane; until then its registry entry
honors `legacy_token_env: GRAPHITI_MCP_TOKEN` for the tunnel path.
