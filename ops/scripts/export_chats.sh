#!/usr/bin/env bash
# === SUITE 6 CANONICAL HEADER ===
# suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
# version: "6.0.0"
# component_id: "OPS-EXP-001"
# component_name: "Chat Export Service"
# layer: "operations"
# domain: "telemetry"
# type: "exporter"
# status: "active"
# created: "2025-10-06T17:10:32Z"
# updated: "2025-11-08T00:00:00Z"
# author: "Igor Beylin"
# maintainer: "Igor Beylin"
#
# === GOVERNANCE METADATA ===
# governance_level: "critical"
# compliance_required: true
# audit_trail: true
# security_classification: "internal"
#
# === TECHNICAL METADATA ===
# dependencies: ["bash", "cp", "find"]
# integrates_with: ["OPS-LEA-001", "TEL-COL-001"]
# data_sources: ["cursor_local_storage"]
# outputs: ["ops/logs/chat_exports"]
#
# === OPERATIONAL METADATA ===
# execution_mode: "scheduled"
# monitoring_required: true
# logging_level: "info"
# performance_tier: "background"
# schedule: "hourly"
#
# === BUSINESS METADATA ===
# purpose: "Export Cursor chat history for learning system analysis"
# summary: "Automated hourly snapshot of Cursor chat data with retention policy"
# business_value: "Enables recursive learning and pattern detection"
# success_metrics: ["export_success_rate >= 99%", "retention_policy_enforced", "log_rotation_functional"]
#
# === TAGS & CLASSIFICATION ===
# tags: ["chat", "export", "telemetry", "automation", "hourly"]
# keywords: ["cursor", "chat", "leveldb", "export", "backup"]
# related_components: ["OPS-LEA-001", "INT-LE-001", "TEL-COL-001"]

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
