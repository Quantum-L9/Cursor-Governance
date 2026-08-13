#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
require_macos
require_diagnosis
command -v ncdu >/dev/null 2>&1 || die "ncdu is not installed. Install it separately, then rerun this command."

REPORT_DIR="$(latest_report_dir_from_state)"
SCAN_ROOT_ARG="${1:-$HOME}"
require_existing_dir "$SCAN_ROOT_ARG" "scan root"
OUTPUT="$REPORT_DIR/ncdu-$(date '+%Y%m%dT%H%M%S').scan"
EXCLUDES="$ROOT_DIR/config/scan-excludes.txt"
ARGS=(-x -o "$OUTPUT")
while IFS= read -r pattern; do
  case "$pattern" in ''|'#'*) continue ;; esac
  ARGS+=(--exclude "$pattern")
done < "$EXCLUDES"
ARGS+=("$SCAN_ROOT_ARG")

log "Scanning $SCAN_ROOT_ARG once and saving reusable results to $OUTPUT"
ncdu "${ARGS[@]}"
printf '%s\n' "$OUTPUT" > "$(state_dir)/latest-ncdu-scan"
log "Saved scan. Reopen instantly with: ncdu -f '$OUTPUT'"
