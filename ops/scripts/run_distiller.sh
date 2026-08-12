#!/usr/bin/env bash
# RETIRED (2026-08-12): Mac LaunchAgent / Dropbox daily cron path.
#
# Batch distill no longer runs on the laptop. SessionEnd enqueues a redacted
# job to S3; GitHub Actions workflow memory-distill.yml processes the queue
# (OpenAI via AWS SM → Graphiti HTTPS). This wrapper remains as a local
# operator entrypoint that invokes the same worker module.
#
# One-time unload of the old LaunchAgent (if still present):
#   launchctl bootout "gui/$(id -u)/com.l9.transcript-distiller" 2>/dev/null || true
#   rm -f ~/Library/LaunchAgents/com.l9.transcript-distiller.plist
#
# Logs (legacy): ~/.cursor-governance/ops/logs/distiller_cron.log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
LOG_FILE="$LOG_DIR/distiller_cron.log"

mkdir -p "$LOG_DIR"

{
  echo ""
  echo "========================================"
  echo "[$(date)] Distiller worker (Graphiti queue) started"
  echo "[$(date)] DEPRECATED LaunchAgent path — prefer GHA memory-distill.yml"
} >> "$LOG_FILE"

PY="${GOV_ROOT}/.venv/bin/python3"
[[ -x "$PY" ]] || PY="python3"

cd "$GOV_ROOT"
set +e
PYTHONPATH="$GOV_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  "$PY" -m ops.graphiti.distill_queue.worker "$@" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [[ "$EXIT_CODE" -eq 0 ]]; then
  echo "[$(date)] Distiller completed successfully" >> "$LOG_FILE"
else
  echo "[$(date)] Distiller failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

if [[ -f "$LOG_FILE" ]] && [[ "$(stat -f%z "$LOG_FILE" 2>/dev/null || echo 0)" -gt 2097152 ]]; then
  tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
  echo "[$(date)] Log rotated" >> "$LOG_FILE"
fi

echo "[$(date)] Distiller cron finished" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
exit "$EXIT_CODE"
