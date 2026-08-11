# T7 — UserRequired desktop gate

CLI pin + verify are **complete**. Cursor must fully restart to load the new managed entry.

## Do this

1. **Quit Cursor completely** (Cursor → Quit Cursor), not only close the window.
2. Reopen Cursor on any workspace.
3. Open **Settings → Tools & MCP**.
4. Confirm server `l9-graphite-memory` is connected and tools appear.
5. Optional: in chat, call a memory health/search tool and confirm it responds.

## Already proven (no restart needed for these)

- `~/.cursor/mcp.json` command = `/Users/ib-mac/l9-graphiti-memory/.venv/bin/python`
- `client cursor verify` ProbeReceipt `status=complete` (22 tools, health complete)
- Backup: `~/.cursor/mcp.json.backup.20260807T145242Z.0ad9f9ad0bfb`

## Rollback if needed

```bash
INTERPRETER=/Users/ib-mac/l9-graphiti-memory/.venv/bin/python
$INTERPRETER -m l9_graphite_memory.cli client cursor uninstall \
  --restore-backup ~/.cursor/mcp.json.backup.20260807T145242Z.0ad9f9ad0bfb
```
