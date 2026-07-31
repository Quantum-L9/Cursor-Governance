<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/docs/MEMORY_TOPOLOGY.md
layer: doc
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-28
/L9_META -->

# Memory Topology — one server, N surfaces

## 1. The requirement

All agents write to the **same** memory graph. That means one long-running
memory endpoint that every surface can reach, with per-agent bearer tokens.
Loopback (`127.0.0.1`) shares only within one host/container: it works for the
Cursor Mac (via the C1 SSH tunnel) but is unreachable from Manus sandboxes,
Claude Code Web/Mobile sandboxes, and Codex cloud. Cloud agents require a
**routable HTTPS host**.

## 2. Deployment options (choose one; Option A is the current live pattern)

| Option | What runs where | Reaches cloud agents? | Identity enforcement |
|---|---|---|---|
| **A. C1 VPS, direct HTTPS (recommended)** | `l9-memory-server --transport http` on C1 (46.62.243.82) behind a TLS reverse proxy (Caddy/nginx) on e.g. `memory.<your-domain>` | Yes | `auth_tokens.json` rendered from the agent registry — one principal per agent |
| B. C1 VPS, tunnel-only (status quo) | Graphiti MCP on C1, SSH tunnel `localhost:8100` per machine | **No** — only machines that can hold an SSH tunnel | `USER_ID` env per machine (weaker; no per-agent token) |
| C. Per-host loopback (`127.0.0.1:8200`) | one server per host | No | local principal only |

Option A is the only topology that satisfies "all LLMs write to the same
memory." Options B/C remain valid for single-machine work but cannot be the
shared plane.

## 3. Option A wiring (C1)

```bash
# On C1 (as root or a service user) — l9-graphiti-memory v2.3+
python -m pip install 'l9-graphite-memory[server]'
# Render per-agent principals from the registry (run wherever governance is cloned):
python3 environment/agents/tools/render_principals.py \
  --root     environment/agents \
  --out-dir  ~/.config/l9-memory \
  --registry agent_registry.yaml \
  --tokens   agent_tokens.local.json \
  --out      auth_tokens.json
# (--registry/--tokens/--out are relative under --root/--out-dir only)
# Start (systemd unit recommended; http_auth_required stays true):
l9-memory-server --transport http --host 127.0.0.1 --port 8200
# TLS proxy: memory.<domain> -> 127.0.0.1:8200  (Caddy: `reverse_proxy 127.0.0.1:8200`)
```

Every surface then sets `L9_MEMORY_HTTP_URL=https://memory.<domain>` and its own
`L9_MEMORY_TOKEN__<AGENT>` (exposed to the adapter under the generic
`L9_MEMORY_CLIENT_TOKEN` name each MCP template expands).

## 4. Non-negotiables

`http_auth_required` stays `true` on any routable bind — the server refuses to
start unauthenticated on a non-loopback host by design. One bearer token per
agent, never shared, rotated independently. The Graphiti/Neo4j projection stays
where it is; the canonical write path is the memory control plane, and the graph
is a rebuildable projection. `group_id` resolution is unchanged
(`ops/graphiti/group_registry.yaml`); this document changes **reachability and
identity**, not namespace semantics.

## 5. Known unknowns (stated, not fabricated)

The exact domain name, TLS termination choice, and whether C1 keeps the legacy
Graphiti MCP (`:8100`) alongside the control plane (`:8200`) are operator
decisions not encoded here. The legacy Cursor tunnel path keeps working during
migration; Cursor's registry entry honors its deployed `GRAPHITI_MCP_TOKEN` via
`legacy_token_env`.
