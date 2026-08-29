# L9 Cursor MCP configuration

**Authority:** `environment/mcp/master.mcp.json`  
**Wired to:** Cursor `~/.cursor/mcp.json` (symlink via `setup_workspace_symlinks.sh`)

This file is the **Cursor CLI** MCP map. It is **not** Claude Code’s map.

| Surface | MCP authority | Graphiti |
|---|---|---|
| Cursor | this file | local SSH tunnel `127.0.0.1:8100` + `graphiti_memory_client.py` |
| Claude Code | `environment/agents/adapters/claude-code/mcp.template.json` | `${GRAPHITI_MCP_URL}` (HTTPS, no bearer) |

Do not unify those two. Cursor outranks Claude Code (`CANONICAL_LAW.md` §2.1).

## Capability broker — retired

The broker (`L9_CAPABILITY_BROKER_URL`, `broker.quantumaipartners.com`) never
shipped. `make broker-serve` prints RETIRED. See `ops/secrets/RETIRED.md`.

GitHub, Context7, Semgrep, and GitGuardian are **not** listed here. Install
them as Cursor-native MCP servers (marketplace / user config). Routing them
through a dead broker made every session report DEGRADED.

## What this file does list

- **graphiti-memory** — operator tunnel (no cloud broker)
- **Playwright**, **n8n-workflows Docs** — local / public, no secret
- **firecrawl-mcp**, **Tavily Expert** — env-var URLs/keys on the trusted operator plane

## Adding a server

Credential-free: add a `command`/`args` block here.

Credential-bearing: install it in Cursor’s user MCP UI or a **user-local**
config, not as `${L9_CAPABILITY_BROKER_URL}/mcp`. Do not paste tokens into
this git-tracked file.

## Wiring check

```bash
cd ~/.cursor-governance
make wiring-check
ls -l ~/.cursor/mcp.json
# should resolve to this repo's environment/mcp/master.mcp.json
```

Historical broker write-up: `MIGRATION_TO_BROKER.md` and
`CAPABILITY_BROKER_COMPLETE.md` (retired banners; do not follow).
