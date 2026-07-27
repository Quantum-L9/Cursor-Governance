#!/usr/bin/env bash
# L9_META
#   l9_schema: 1
#   artifact_type: exporter
#   component: chat_export_service
#   tags: [chat, export, telemetry, automation, hourly]
#   retrieval: on_demand
#   status: active
#
# Export Cursor chat history for learning system analysis

set -euo pipefail

# Anchor to script location, not current working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$SCRIPT_DIR/../logs/chat_exports"
LOGDIR="$SCRIPT_DIR/../logs"
STAMP=$(date +%Y-%m-%d_%H-%M-%S)
LOG_OUT="$LOGDIR/chat_export_launchd.out"
LOG_ERR="$LOGDIR/chat_export_launchd.err"

mkdir -p "$LOGDIR"

# ---------------------------------------------------------------------------
# Source 1: Legacy workspaceStorage (SQLite/LevelDB — old format)
# ---------------------------------------------------------------------------
LEGACY_SRC="$HOME/Library/Application Support/Cursor/User/workspaceStorage"
LEGACY_DEST="$DEST/$STAMP/User/workspaceStorage"

if [ -d "$LEGACY_SRC" ]; then
    mkdir -p "$LEGACY_DEST"
    if cp -R "$LEGACY_SRC/" "$LEGACY_DEST/"; then
        echo "[$(date)] Legacy workspace export completed: $STAMP" >> "$LOG_OUT"
    else
        echo "[$(date)] WARNING: Legacy workspace copy failed" >> "$LOG_ERR"
    fi
else
    echo "[$(date)] INFO: No legacy workspace data at $LEGACY_SRC (expected)" >> "$LOG_OUT"
fi

# ---------------------------------------------------------------------------
# Source 2: Agent transcripts (new plain-text format)
#   Location: ~/.cursor/projects/*/agent-transcripts/*.txt
# ---------------------------------------------------------------------------
TRANSCRIPT_SRC="$HOME/.cursor/projects"
TRANSCRIPT_DEST="$DEST/$STAMP/agent-transcripts"

transcript_count=0
if [ -d "$TRANSCRIPT_SRC" ]; then
    mkdir -p "$TRANSCRIPT_DEST"
    # Copy all agent-transcripts directories, preserving project structure
    for project_dir in "$TRANSCRIPT_SRC"/*/agent-transcripts; do
        [ -d "$project_dir" ] || continue
        project_name="$(basename "$(dirname "$project_dir")")"
        target="$TRANSCRIPT_DEST/$project_name"
        mkdir -p "$target"
        # Copy only .txt files (transcripts)
        for txt_file in "$project_dir"/*.txt; do
            [ -f "$txt_file" ] || continue
            cp "$txt_file" "$target/"
            transcript_count=$((transcript_count + 1))
        done
    done
    echo "[$(date)] Agent transcripts exported: $transcript_count files" >> "$LOG_OUT"
else
    echo "[$(date)] INFO: No agent transcripts at $TRANSCRIPT_SRC" >> "$LOG_OUT"
fi

# ---------------------------------------------------------------------------
# Retention policy: keep only last 10 snapshots
# ---------------------------------------------------------------------------
find "$DEST" -maxdepth 1 -type d -name "20*" | sort | head -n -10 | xargs rm -rf 2>/dev/null || true
echo "[$(date)] Retention cleanup completed" >> "$LOG_OUT"

# ---------------------------------------------------------------------------
# Log rotation: keep logs under 1MB
# ---------------------------------------------------------------------------
for logfile in "$LOG_OUT" "$LOG_ERR"; do
    if [ -f "$logfile" ] && [ "$(stat -f%z "$logfile" 2>/dev/null || echo 0)" -gt 1048576 ]; then
        tail -n 500 "$logfile" > "${logfile}.tmp" && mv "${logfile}.tmp" "$logfile"
        echo "[$(date)] Log rotated: $logfile" >> "$LOG_OUT"
    fi
done
