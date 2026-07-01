#!/usr/bin/env bash
# L9 Transcript Distiller — daily cron wrapper
# Runs at 5am via launchd, distills yesterday's transcripts.
#
# Logs: ~/.cursor-governance/ops/logs/distiller_cron.log
# Reports: ~/.cursor-governance/ops/logs/distiller_reports/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
LOG_FILE="$LOG_DIR/distiller_cron.log"
L9_ROOT="$HOME/Projects/L9"

mkdir -p "$LOG_DIR"

echo "" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "[$(date)] Distiller cron started" >> "$LOG_FILE"

# Load env vars (API keys, model config)
if [ -f "$L9_ROOT/.env.local" ]; then
    set -a
    source "$L9_ROOT/.env.local"
    set +a
fi

# Calculate yesterday's date (macOS date syntax)
YESTERDAY=$(date -v-1d +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)

echo "[$(date)] Processing transcripts from $YESTERDAY" >> "$LOG_FILE"

# Run distiller for yesterday's transcripts
python3 "$SCRIPT_DIR/transcript_distiller.py" \
    --source transcripts \
    --since "$YESTERDAY" \
    --until "$TODAY" \
    --l9-root "$L9_ROOT" \
    >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date)] Distiller completed successfully" >> "$LOG_FILE"
else
    echo "[$(date)] Distiller failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

# Log rotation: keep under 2MB
if [ -f "$LOG_FILE" ] && [ "$(stat -f%z "$LOG_FILE" 2>/dev/null || echo 0)" -gt 2097152 ]; then
    tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
    echo "[$(date)] Log rotated" >> "$LOG_FILE"
fi

echo "[$(date)] Distiller cron finished" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
