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
SRC="$HOME/Library/Application Support/Cursor/User/workspaceStorage"
DEST="$SCRIPT_DIR/../logs/chat_exports"
STAMP=$(date +%Y-%m-%d_%H-%M-%S)
CHAT_DEST="$DEST/$STAMP/User/workspaceStorage"

# Create destination directory
mkdir -p "$CHAT_DEST"

# Check if source exists
if [ ! -d "$SRC" ]; then
    echo "[$(date)] ERROR: No chat data found at $SRC" >> "$SCRIPT_DIR/../logs/chat_export_launchd.err"
    exit 1
fi

# Copy chat data with proper error handling
if cp -R "$SRC/" "$CHAT_DEST/"; then
    echo "[$(date)] Chat export completed: $STAMP" >> "$SCRIPT_DIR/../logs/chat_export_launchd.out"
    
    # Retention policy: keep only last 10 backups (safer sorting)
    find "$DEST" -maxdepth 1 -type d -name "20*" | sort | tail -n +11 | xargs rm -rf 2>/dev/null || true
    
    echo "[$(date)] Retention cleanup completed" >> "$SCRIPT_DIR/../logs/chat_export_launchd.out"
    
    # Log rotation: keep logs under 1MB
    for logfile in "$SCRIPT_DIR/../logs/chat_export_launchd.out" "$SCRIPT_DIR/../logs/chat_export_launchd.err"; do
        if [ -f "$logfile" ] && [ $(stat -f%z "$logfile" 2>/dev/null || echo 0) -gt 1048576 ]; then
            tail -n 500 "$logfile" > "${logfile}.tmp" && mv "${logfile}.tmp" "$logfile"
            echo "[$(date)] Log rotated: $logfile" >> "$SCRIPT_DIR/../logs/chat_export_launchd.out"
        fi
    done
else
    echo "[$(date)] ERROR: Copy failed for $SRC" >> "$SCRIPT_DIR/../logs/chat_export_launchd.err"
    exit 1
fi
