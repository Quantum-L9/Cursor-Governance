#!/usr/bin/env bash
# Wrapper for governance-monitor.py

# Find GlobalCommands
if [ -d "$HOME/Dropbox/Cursor Governance/GlobalCommands" ]; then
    GLOBAL_COMMANDS="$HOME/Dropbox/Cursor Governance/GlobalCommands"
elif [ -d "$HOME/Library/Application Support/Cursor/GlobalCommands" ]; then
    GLOBAL_COMMANDS="$HOME/Library/Application Support/Cursor/GlobalCommands"
fi

MONITOR_SCRIPT="$GLOBAL_COMMANDS/ops/scripts/governance-monitor.py"
LOG_FILE="$GLOBAL_COMMANDS/ops/logs/governance_monitor_launchd.out"

echo "[$(date)] Running governance monitor..." >> "$LOG_FILE"

if [ -f "$MONITOR_SCRIPT" ]; then
    python3 "$MONITOR_SCRIPT" >> "$LOG_FILE" 2>&1
    echo "[$(date)] Governance monitor completed" >> "$LOG_FILE"
else
    echo "[$(date)] Error: governance-monitor.py not found" >> "$LOG_FILE"
fi
