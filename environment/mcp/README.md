# L9 Master MCP Configuration

**Authority**: `environment/mcp/master.mcp.json`

**Wired to**:
- Cursor: `~/.cursor/mcp.json` (symlink)
- Claude Code CLI: `~/.claude/mcp.json` (symlink)
- Cloud adapters: per-surface `mcp.template.json` (env-var refs)

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
