# L9 Master MCP Configuration

**Authority**: `environment/mcp/master.mcp.json`

**Wired to**:
- Cursor: `~/.cursor/mcp.json` — a **real per-machine file** rendered by
  `ops/memory/mcp_instantiation.py` (`make memory-mcp-install`; `--check` via
  `make memory-mcp-check`). It is no longer a symlink: the memory package
  configurator refuses a symlinked target, and a symlink cannot carry a
  per-machine entry. The renderer replaces an existing symlink in place.
- Claude Desktop: `claude_desktop_config.json` (rendered — `make claude-desktop-install`;
  see `environment/agents/adapters/claude-desktop/README.md`)
- Cloud adapters: per-surface `mcp.template.json` (env-var refs)

## Adding an MCP server

1. Add the entry here (machine surfaces) and, for Claude Code web/mobile, to
   `environment/agents/adapters/claude-code/mcp.template.json` with every
   credential as `${VAR}` under `_requires_env` / `_optional_headers`.
2. `make claude-projection` renders `.mcp.json`; `make memory-mcp-install`
   renders Cursor; `make claude-desktop-install` renders Claude Desktop
   (stdio only, absolute commands, no `${VAR}`, no secrets).
3. Restart the client. Never write a credential value into any of these files.

## Canonical memory server

`l9-graphite-memory` (MemoryService over stdio, `memory-control-plane/v1`) is
owned by the memory package and is **never authored in this inventory**. Every
renderer hands that one entry to the package's configurator
(`l9-memory client cursor install --path …`) against the runtime this checkout
is bound to (`ops/config/memory-binding.json`, proven by
`ops/memory/runtime_binding.py`), and proves it with the package's own
`client cursor verify --path` handshake (`make memory-mcp-install
MEMORY_VERIFY_MCP=1`). Claude Code's template declares the same argv gated on
`L9_MEMORY_INTERPRETER`.

The legacy direct-provider front door (`graphiti-memory` over a provider URL)
was retired at realignment stage C7/C8. Renderers drop that key from every
file they write; no template declares it; `ops/scripts/validate_memory_egress_boundary.py`
keeps it out of production configuration.

## Capability broker (retired)

The capability-broker experiment never shipped. Credential-bearing MCP servers
that pointed at `${L9_CAPABILITY_BROKER_URL}/mcp` are removed. Archived docs
and code: `ops/secrets/_archived/capability-broker/`.

Do not paste `SONAR_TOKEN`, `SEMGREP_APP_TOKEN`, `INFISICAL_CLIENT_SECRET`, or
any memory credential into a model-controlled environment to work around that.

## GitMCP dogfood (ChatGPT)

GitMCP is a temporary **read/search reconnaissance surface** over the public
repository. Operator runbook: [CHATGPT_GITMCP_DOGFOOD.md](CHATGPT_GITMCP_DOGFOOD.md).

- It does not replace `environment/mcp/master.mcp.json` as MCP configuration authority.
- It does not activate the Program Execution ChatGPT adapter.
- It does not grant write or execution authority.
- Native Cursor-Governance MCP design follows dogfood evidence.
