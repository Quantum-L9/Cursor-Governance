#!/usr/bin/env bash
# Wrapper for governance-monitor.py

# Find GlobalCommands
if [ -d "$HOME/.cursor-governance" ]; then
    GLOBAL_COMMANDS="$HOME/.cursor-governance"
elif [ -d "$HOME/.cursor-governance" ]; then
    GLOBAL_COMMANDS="$HOME/.cursor-governance"
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
