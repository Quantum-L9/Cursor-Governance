# ADR-0053: A dormant trusted stdio bridge may speak Memory 3.0 signed-agent HTTP

## Status

Accepted

This record admits a dormant consumer adapter. It does not activate the
bridge, rebind the Memory 2.6.0 pin, or admit a model-facing HTTP client.

## Date

2026-10-26

## Context

Memory 3.0 source (`eb0bcbed`) serves signed-agent MCP on `POST /mcp` with
protocol revisions `2025-11-25` and `2025-06-18`. Cursor and Claude Code
speak stdio protocol `2024-11-05` to a local command. CANONICAL_LAW §8.5.4
still seals `L9_MEMORY_HTTP_*` and any model-selected HTTP memory client.
The hosted Memory exception in Quantum-L9/.github is unchanged.

## Decision

`ops/memory/remote_stdio_bridge.py` is the one Cursor-Governance module that
may open HTTPS to that endpoint, and only when the process environment sets
`L9_MEMORY_REMOTE_STDIO=1`. The generated MCP entries stay stdio commands.
They do not carry a remote URL, a bearer, or a signing key.

The bridge re-mints the existing agent assertion and identity HMAC on every
request from the actor derived by `ops/memory/agent_identity.py`. The signing
key stays in the trusted process. An ephemeral key minted inside a hosted
container is not a durable hosted identity and is refused. There is no local
SQLite fallback when the remote call fails.

`ops/config/memory-binding.json` remains pinned to Memory 2.6.0. Selecting
the bridge in a live Cursor, Claude Desktop, or Claude Code session is a
later activation gate.

## Consequences

- Default launch behavior is the local 2.6.0 stdio server.
- A missing URL, key, or a contract mismatch is an error, not a local write.
- `memory.distill` and `memory.bootstrap` are not added as remote tools.
- Context7's vault bridge is a different static-credential adapter and is
  not this path.
