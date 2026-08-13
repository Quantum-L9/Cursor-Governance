#!/bin/bash
# l9-mac-storage-triage / scripts/actions/empty-trash.sh
# purpose: empty the current user's Trash only
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
load_env
list_has_action empty_trash || die "empty_trash is not approved."
is_true "${EMPTY_TRASH_APPROVED:-false}" || die "EMPTY_TRASH_APPROVED must be true."
require_safe_user_delete_path "$HOME/.Trash"

STARTED_AT="$(now_iso)"
REPORT_DIR="$(latest_report_dir_from_state)"
mkdir -p "$REPORT_DIR/actions"
LOG_FILE="$REPORT_DIR/actions/empty-trash.log"
BEFORE_FREE="$(free_kib_for_path "$DATA_VOLUME")"
STATUS=success
: > "$LOG_FILE"

if osascript -e 'tell application "Finder" to empty the trash' >>"$LOG_FILE" 2>&1; then
  printf 'OK finder_empty_trash\n' >> "$LOG_FILE"
else
  printf 'FALLBACK rm_trash\n' >> "$LOG_FILE"
  if find "$HOME/.Trash" -mindepth 1 -maxdepth 1 -exec rm -rf {} + >>"$LOG_FILE" 2>&1; then
    printf 'OK rm_trash\n' >> "$LOG_FILE"
  else
    printf 'FAIL empty_trash\n' >> "$LOG_FILE"
    STATUS=fail
  fi
fi

AFTER_FREE="$(free_kib_for_path "$DATA_VOLUME")"
printf 'free_kib_before=%s\nfree_kib_after=%s\n' "$BEFORE_FREE" "$AFTER_FREE" >> "$LOG_FILE"
FINISHED_AT="$(now_iso)"
write_action_receipt empty_trash "$STATUS" "$STARTED_AT" "$FINISHED_AT" "$LOG_FILE" >/dev/null
[ "$STATUS" = success ] || exit 1
