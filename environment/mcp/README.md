# L9 Master MCP Configuration

**Authority**: `environment/mcp/master.mcp.json`

**Wired to**:
- Cursor: `~/.cursor/mcp.json` (symlink)
- Claude Code CLI: `~/.claude/mcp.json` (symlink)
- Claude Desktop: `claude_desktop_config.json` (rendered — `make claude-desktop-install`;
  see `environment/agents/adapters/claude-desktop/README.md`)
- Cloud adapters: per-surface `mcp.template.json` (env-var refs)

## Adding an MCP server

1. Add the entry here (machine surfaces) and, for Claude Code web/mobile, to
   `environment/agents/adapters/claude-code/mcp.template.json` with every
   credential as `${VAR}` under `_requires_env` / `_optional_headers`.
2. `make claude-projection` renders `.mcp.json`; `make claude-desktop-install`
   renders Claude Desktop (stdio only, absolute commands, no `${VAR}`, no secrets).
3. Restart the client. Never write a credential value into any of these files.

## Canonical memory server

`l9-graphite-memory` is owned by the memory package. Claude Code's template
declares it gated on `L9_MEMORY_INTERPRETER`; on machine surfaces the package's
configurator writes it (`l9-memory client cursor install [--path …]`), never
this file. The `graphiti-memory` entries are the legacy direct-provider front
door, retired at realignment stage C7/C8.

## Graphiti

| Surface | URL |
|---|---|
| Cursor (this machine) | `http://127.0.0.1:8100/mcp` (SSH tunnel) |
| Cloud adapters | `${GRAPHITI_MCP_URL}` — default `https://memory.quantumaipartners.com/graphiti/mcp` |

**No bearer** in any adapter template. `GRAPHITI_MCP_TOKEN` is deliberately absent.

## Capability broker (retired)

The capability-broker experiment never shipped. Credential-bearing MCP servers
that pointed at `${L9_CAPABILITY_BROKER_URL}/mcp` are removed. Archived docs
and code: `ops/secrets/_archived/capability-broker/`.

Do not paste `SONAR_TOKEN`, `SEMGREP_APP_TOKEN`, `INFISICAL_CLIENT_SECRET`, or a
Graphiti bearer into a model-controlled environment to work around that.
