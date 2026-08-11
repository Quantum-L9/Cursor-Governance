# Agent UI Control — Cursor operator guide

## Authority (fail-closed)

1. **Surface:** SQL client already connected to `UCSCIETRADE` / `cieTrade_SM` (SSMS or Azure Data Studio).
2. **Forbidden:** cieTrade ERP application UI.
3. **SQL authority:** Cursor authors and executes SQL, including explore/extract writes.
4. **Write policy:** Prefer SELECT + file export. Temp/staging/`sqlcmd`/`bcp` OK. No casual live `UPDATE`/`DELETE`.
5. **Transport:** `~/.l9/mac_tasks` primary. Reverse tunnel **opt-in only** (`install_remote_tunnel.sh`).
6. **Integrity:** Accept extract files only when `size > 0` and `nonzero_bytes > 0`.

## CLI

```bash
PACK="$HOME/.cursor-governance/tools/l9_agent_ui_control"
# Ensure runner is up (LaunchAgent or: python3 "$PACK/runner.py")

python3 "$PACK/local_console.py" shell --cmd 'echo ok'
python3 "$PACK/local_console.py" shell --cmd 'sqlcmd -S UCSCIETRADE -E -d cieTrade_SM -Q "SELECT 1"'
# Pipes/operators need explicit bash wrap (runner always uses shell=False):
python3 "$PACK/local_console.py" shell --bash --cmd 'command -v sqlcmd || echo SQLCMD_ABSENT'
python3 "$PACK/local_console.py" sql-studio --file /path/to/query.sql
python3 "$PACK/local_console.py" status --task-id task-…
```

### Completed result schema (minimum)

```json
{
  "task_id": "task-…",
  "completed_at": 0.0,
  "result": {
    "status": "done",
    "stdout": "ok\n",
    "stderr": "",
    "exit_code": 0
  }
}
```

## Primary vs fallback

| Path | When |
|------|------|
| `shell` → `sqlcmd`/`bcp` | On PATH (IB-PC via RDP shell, or Mac if installed) — **primary for bulk extract** |
| `sql-studio` | Interactive client is the only reachable surface — **fallback** |

Probe: `command -v sqlcmd` (this Mac often has none; use IB-PC oneshot or Windows App shell).

## Extract integrity

```bash
python3 "$PACK/integrity_check.py" \
  "/path/to/Current Work - IGNORE/CieTrade Data Extraction/<stamp>"
```

Reject the known-corrupt baseline `cieTrade_export_20260807_183800` (84/84 null-filled CSVs).

## SSMS Grid extract (Windows App → IB-PC) — canonical

**DB:** `cieTrade_SM_EXPORT` · **Output mode:** Results to **Grid** only (never Results to File / Ctrl+T).

```bash
PACK="$HOME/.cursor-governance/tools/l9_agent_ui_control"
PY="${L9_AGENT_UI_PYTHON:-$HOME/.cursor-governance/.venv/bin/python}"

# Full cycle: paste into UPPER editor → F5 → LOWER grid Ctrl+A → Ctrl+Shift+C → Mac file
"$PY" "$PACK/drive_ssms_extract.py" \
  --file /path/to/query.sql \
  --out /path/to/out.csv \
  --wait-exec 6

# If results already on screen: copy LOWER grid only
"$PY" "$PACK/drive_ssms_extract.py" --copy-only --out /path/to/out.csv
```

| Step | Where | Action |
|------|--------|--------|
| 1 | Raise `IB-PC` window | Not Windows App **Devices** |
| 2 | UPPER editor | Clear → paste SQL |
| 3 | Execute | **F5** (play). Keep Grid |
| 4 | LOWER Results grid | Click grid → **Ctrl+A** → **Ctrl+Shift+C** (Copy with Headers) |
| 5 | Mac | `pbpaste` → file; reject if clipboard looks like SQL |

**Never:** Cmd/Ctrl+N, Alt menu letters, copying the editor, Windows App file drag.

## Phase B workflow

1. Census tables/columns/row estimates (agent-authored SQL).
2. Probe `TOP (N)` on payment-like tables.
3. Rank for PlasticOS (payment history first).
4. Extract under `Current Work - IGNORE/CieTrade Data Extraction/<stamp>/`.
5. Run `integrity_check.py`; write `EXTRACT_MANIFEST.md`.
