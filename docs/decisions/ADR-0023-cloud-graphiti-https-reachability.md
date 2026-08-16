# ADR-0023: Cloud Graphiti HTTPS reachability

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
