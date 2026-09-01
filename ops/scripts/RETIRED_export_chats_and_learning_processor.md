# Retired: hourly chat export + tenx learning processor

**Status:** retired 2026-08-13  
**Replacement:** Cursor `sessionEnd` (chat X'd out) →
`python -m ops.graphiti.hydration.archive_transcript` →
S3 bucket `l9-chat-transcripts-020125249784` (`v1/<conversation_id>.json`).

## Why

`ops/scripts/export_chats.sh` and LaunchAgent `com.tenx.chat-export` copied
Cursor `workspaceStorage` SQLite hourly (109 GB on this Mac) and looked for
flat `*.txt` transcripts. Cursor writes nested `.jsonl`. The copies were not
the chat words.

`com.tenx.learning-processor` → `memory_aggregator.py` used a retired
Dropbox path for SQLite/LevelDB chat dumps (forbidden as SSOT; that path
does not exist). Hourly log: `No chat exports found`. It never parsed `.jsonl`.

Local or GitHub copies are useless across machines. Closed-chat words go to S3.

## What is stored now

On session close: user/assistant **text only**, plus timestamps when Cursor
embedded them. No tool dumps, no sqlite, no git_status wrappers.

## Operator

```bash
# unload dead jobs (also: com.tenx.cursor-governance leftover monitor)
launchctl bootout "gui/$(id -u)/com.tenx.cursor-governance" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.tenx.chat-export" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.tenx.learning-processor" 2>/dev/null || true

# archive one closed chat (also runs from sessionEnd automatically)
python -m ops.graphiti.hydration.archive_transcript --session-id "<uuid>" --project-dir "$(pwd)"

# backfill existing ~/.cursor/projects jsonl
python -m ops.graphiti.hydration.archive_transcript --backfill
```

Env: `L9_CHAT_TRANSCRIPT_S3_BUCKET` (default `l9-chat-transcripts-020125249784`).
No expiration lifecycle (Intelligent-Tiering after 30 days).

Do **not** reinstall `install_export_job.sh` or the tenx learning LaunchAgent.
