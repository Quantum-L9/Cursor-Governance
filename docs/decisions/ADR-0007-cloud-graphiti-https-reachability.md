# ADR-0007: Cloud Graphiti HTTPS reachability

## Status

Accepted

## Date

2026-08-12

## Context

ADR-0006 retired the L9 HTTP memory side door (`L9_MEMORY_HTTP_*` /
`memory_client`) and required Cursor Graphiti as the sole episodic front door.
Claude Code Web/Mobile sandboxes cannot use the SSH tunnel to `127.0.0.1:8100`.

## Decision

1. Expose the **same** Graphiti MCP process on C1 behind Caddy at
   `https://memory.quantumaipartners.com/graphiti/*` → `127.0.0.1:8100`.
2. Cloud surfaces set `GRAPHITI_MCP_URL=https://memory.quantumaipartners.com/graphiti/mcp`
   (no trailing slash) and `GRAPHITI_MCP_TOKEN`.
3. Writer attribution remains distinct via `USER_ID` / `L9_MEMORY_AGENT_ID` /
   `L9_MEMORY_SOURCE` — do not revive `L9_MEMORY_CLIENT_TOKEN` for lifecycle.
4. Claude Code gold-standard pack lives at
   `environment/agents/adapters/claude-code/` (transitional symlink at
   `environment/claude-code` extinguished 2026-08-12).

## Consequences

- Front-door tests forbid the HTTP side door, not the public Graphiti hostname.
- `mcp.template.json` uses `${GRAPHITI_MCP_URL}` env expansion.
- Thin adapters inherit the Graphiti carrier contract.

## Related

- ADR-0006 — single memory front door
- ADR-0028 — session hydrate/close visibility and write-primary repair

## Supersession (2026-09-07) — superseded in full by ADR-0030; legacy operator infrastructure only

Every Decision item above describes reaching the **provider** (the Graphiti
MCP process) from a model surface: the Caddy route, `GRAPHITI_MCP_URL`,
`GRAPHITI_MCP_TOKEN`, `${GRAPHITI_MCP_URL}` expansion in `mcp.template.json`.
Since realignment stage C9 no model surface holds a provider URL or bearer,
and since stage C11 no Cursor code path reads or writes the provider at all:
memory is reached only through `ops/memory` to the bound `l9-graphite-memory`
runtime (stdio), and cloud surfaces render the package-owned
`l9-graphite-memory` MCP server only when `L9_MEMORY_INTERPRETER` is bound.
The HTTPS exposure this ADR created is legacy operator infrastructure of the
provider deployment (operator-owned, retired with it); it is not a transport
any adapter, hook, skill or rule may name as live. Writer attribution
(`USER_ID` / `L9_MEMORY_AGENT_ID` / `L9_MEMORY_SOURCE`) and the gold-standard
pack location in item 3–4 remain true and are restated by ADR-0030 and
`CANONICAL_LAW` §8.2.
