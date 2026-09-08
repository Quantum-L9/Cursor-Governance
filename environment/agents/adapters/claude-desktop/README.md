# Claude Desktop adapter — MCP config

Claude Desktop reads `claude_desktop_config.json` (macOS:
`~/Library/Application Support/Claude/claude_desktop_config.json`). It differs
from Claude Code in three ways that make a symlink to the master inventory
wrong: it expands no `${VAR}` references, it accepts only stdio servers
(`command` / `args` / `env`), and as a GUI app it does not inherit a login
shell's `PATH`, so commands must be absolute.

`render_claude_desktop_config.py` is therefore the third consumer of
[`environment/mcp/master.mcp.json`](../../../mcp/master.mcp.json) and renders
rather than links.

## Use

```bash
make claude-desktop-check                 # drift report, writes nothing (exit 2 on drift)
make claude-desktop-install               # atomic write + timestamped backup
L9_MEMORY_INTERPRETER=~/.l9/memory-venv/bin/python make claude-desktop-install MEMORY_VERIFY_MCP=1
```

Then fully quit and relaunch Claude Desktop. Servers appear under the tools
menu in a new chat.

## What renders

| Master entry | Desktop result |
|---|---|
| stdio (`command` + `args`) | copied, `command` resolved to an absolute path |
| `url` / `type: http` | skipped, named in the receipt — add remote servers through Desktop → Settings → Connectors |
| `env` with `${VAR}` for a non-credential variable | expanded from the invoking shell |
| `env` naming a token / key / secret / password / DSN | server skipped: the Desktop file is secret-free (rules/61, ADR-016); carry the credential in a wrapper script the entry launches |
| a server you added in Desktop yourself | preserved byte for byte |
| `l9-graphite-memory` | never authored here; written by `l9-memory client cursor install --path <desktop config>` when `L9_MEMORY_INTERPRETER` is set |

## Adding an MCP server

1. Add the entry to `environment/mcp/master.mcp.json` (Cursor, Claude Code CLI,
   Claude Desktop) and, if Claude Code web/mobile sessions need it, to
   `environment/agents/adapters/claude-code/mcp.template.json` with every
   credential as `${VAR}` under `_requires_env`.
2. `make claude-projection` (Claude Code `.mcp.json`) and
   `make claude-desktop-install` (Desktop).
3. Restart the client.

Never paste a credential value into either file. A server that cannot run
without one is launched through a wrapper that resolves it, or gated out.
