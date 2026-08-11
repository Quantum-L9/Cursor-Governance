# Agent UI Control (`l9_agent_ui_control`)

Local-first Mac control plane for Cursor: file-queue shell/`sqlcmd` primary, SQL Studio GUI fallback.

**Tombstone:** `tools/mac_agent` was replaced by this pack. Do not reintroduce `mac_agent` under `tools/`.

## Quick start

```bash
# From Cursor-Governance (or via .cursor-commands symlink)
cd tools/l9_agent_ui_control
python3 -m compileall .
bash install_local.sh          # LaunchAgent → runner.py (does NOT load tunnel)
python3 runner.py              # or rely on LaunchAgent

# From another terminal / Cursor agent:
python3 local_console.py shell --cmd 'echo ok'
```

See [LOCAL_CURSOR.md](./LOCAL_CURSOR.md) for authority contracts, CLI, and extract integrity gate.

## Layout

| File | Role |
|------|------|
| `runner.py` | LaunchAgent entry; polls `~/.l9/mac_tasks` |
| `local_console.py` | Cursor CLI (shell / sql-studio / status) |
| `task_queue.py` | Local pending/completed queue |
| `integrity_check.py` | Reject null-filled extract files |
| `install_local.sh` | Local install only (no tunnel) |
| `install_remote_tunnel.sh` | Opt-in reverse tunnel |

## Mode

- Default `mode: local` (file queue). Set `L9_AGENT_UI_MODE=remote` only when intentionally using VPS/WebSocket paths.
