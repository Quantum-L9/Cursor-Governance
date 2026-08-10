# ADR-0006: Single memory front door — Cursor Graphiti only

## Status

Accepted (supersedes ADR-0003's dual HTTP hook/MCP plane for Claude lifecycle)

## Date

2026-08-07

## Context

Claude Code grew a parallel HTTP memory plane (`L9_MEMORY_HTTP_URL` /
`memory_client.py` / `l9-shared-memory` @ `memory.quantumaipartners.com`) beside
the Cursor Graphiti lifecycle (`ops/graphiti/graphiti_memory_client.py`). Agents
followed error strings into the Claude folder and treated a missing bearer token
as "memory broken" while Graphiti was healthy. Escape hatches
(`L9_MEMORY_ENFORCEMENT=off`) and a second MCP URL created back doors.

CANONICAL_LAW §2.1 and §8 require Cursor-primary ownership and Graphiti-native
memory. ADR-0005 already states one agent episodic memory; this ADR removes the
structural duplicate.

## Decision

1. **One front door.** All agent episodic memory lifecycle (SessionStart prefetch,
   phase-lock, Stop writeback, PreToolUse gate verification, interactive MCP) goes
   through Cursor Graphiti: `ops/graphiti/graphiti_memory_client.py` and
   `graphiti-memory` @ `127.0.0.1:8100` (SSH tunnel + `GRAPHITI_MCP_TOKEN`).
2. **Claude is a thin wrap.** `environment/claude-code/hooks/memory_*.py` call
   `environment/claude-code/memory/graphiti_bridge.py` only. No HTTP client.
3. **Deleted side doors.** `memory_client.py`, `L9_MEMORY_HTTP_URL` /
   `L9_MEMORY_CLIENT_TOKEN` lifecycle use, `l9-shared-memory` MCP template, and
   `L9_MEMORY_ENFORCEMENT=off` are forbidden residue.
4. **Admin key only.** The sole back door is operator-only
   `L9_MEMORY_ENFORCEMENT_BREAKGLASS` (`agent_settable: false`).

## Consequences

- Claude SessionStart banners report Graphiti group_id, not HTTP token errors
- ADR-0003's "two entry points" remains valid only as hook vs interactive MCP
  **roles**, both on the Graphiti front door — not as two transports/stores
- Web/Mobile sandboxes without the tunnel do not get a second memory plane

## Related

- ADR-0002, ADR-0003 (roles), ADR-0004 (superseded client pin), ADR-0005
- `skills/l9-graphiti-memory/SKILL.md`
- `CANONICAL_LAW.md` §8
