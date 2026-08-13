#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
load_env
list_has_action spotlight_exclusions || die "spotlight_exclusions is not approved."
STARTED_AT="$(now_iso)"
REPORT_DIR="$(latest_report_dir_from_state)"
LOG_FILE="$REPORT_DIR/actions/spotlight-exclusions.log"
MANUAL_FILE="$REPORT_DIR/actions/spotlight-manual-privacy-paths.txt"
mkdir -p "$REPORT_DIR/actions"
: > "$LOG_FILE"
: > "$MANUAL_FILE"
STATUS=success

while IFS= read -r path; do
  case "$path" in ''|'#'*) continue ;; esac
  require_absolute_path "$path" "Spotlight exclusion path"
  if [ ! -d "$path" ]; then
    printf 'MISSING %s\n' "$path" | tee -a "$LOG_FILE"
    STATUS=fail
    continue
  fi
  if cloudstorage_path "$path"; then
    printf '%s\n' "$path" >> "$MANUAL_FILE"
    printf 'MANUAL_FILE_PROVIDER_PRIVACY %s\n' "$path" | tee -a "$LOG_FILE"
    continue
  fi
  if touch "$path/.metadata_never_index" 2>>"$LOG_FILE"; then
    printf 'MARKER_CREATED %s\n' "$path/.metadata_never_index" | tee -a "$LOG_FILE"
  else
    printf 'MARKER_FAILED %s\n' "$path" | tee -a "$LOG_FILE"
    STATUS=fail
  fi
done < "$SPOTLIGHT_EXCLUSIONS_FILE"

FINISHED_AT="$(now_iso)"
write_action_receipt spotlight_exclusions "$STATUS" "$STARTED_AT" "$FINISHED_AT" "$LOG_FILE" >/dev/null
[ "$STATUS" = success ] || exit 1
