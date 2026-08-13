#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
load_env
list_has_action mail_cache_remove || die "mail_cache_remove is not approved."
is_true "$MAIL_CACHE_REMOVE_APPROVED" || die "Mail removal approval is false."
[ "$MAIL_SERVER_BACKED_CONFIRMED" = true ] || die "Server-backed mail confirmation is not true."
[ "$MAIL_LOCAL_ONLY_MAILBOXES_CONFIRMED_ABSENT" = true ] || die "Absence of local-only mailboxes is not confirmed."
require_safe_user_delete_path "$MAIL_DATA_PATH"
STARTED_AT="$(now_iso)"
REPORT_DIR="$(latest_report_dir_from_state)"
LOG_FILE="$REPORT_DIR/actions/mail-cache-remove.log"
mkdir -p "$REPORT_DIR/actions"
BEFORE_FREE="$(free_kib_for_path "$DATA_VOLUME")"

osascript -e 'quit app "Mail"' >>"$LOG_FILE" 2>&1 || true
pkill -x Mail >>"$LOG_FILE" 2>&1 || true
pkill -x MailServiceAgent >>"$LOG_FILE" 2>&1 || true
sleep 2

PATHS=(
  "$MAIL_DATA_PATH"
  "$HOME/Library/Mail Downloads"
  "$HOME/Library/Containers/com.apple.mail"
  "$HOME/Library/Containers/com.apple.MailServiceAgent"
  "$HOME/Library/Application Scripts/com.apple.mail"
  "$HOME/Library/Application Scripts/com.apple.MailServiceAgent"
  "$HOME/Library/Caches/com.apple.mail"
  "$HOME/Library/Saved Application State/com.apple.mail.savedState"
  "$HOME/Library/Preferences/com.apple.mail.plist"
  "$HOME/Library/Preferences/com.apple.MailServiceAgent.plist"
  "$HOME/Library/Metadata/Mail"
)
STATUS=success
for path in "${PATHS[@]}"; do
  if [ -e "$path" ]; then
    if rm -rf "$path" >>"$LOG_FILE" 2>&1; then
      printf 'REMOVED %s\n' "$path" >> "$LOG_FILE"
    else
      printf 'REMOVE_FAILED %s\n' "$path" >> "$LOG_FILE"
      STATUS=fail
    fi
  fi
done

if [ -e "$MAIL_DATA_PATH" ]; then
  printf 'PRIMARY_MAIL_PATH_REMAINS %s\n' "$MAIL_DATA_PATH" >> "$LOG_FILE"
  STATUS=fail
fi
AFTER_FREE="$(free_kib_for_path "$DATA_VOLUME")"
printf 'free_kib_before=%s\nfree_kib_after=%s\n' "$BEFORE_FREE" "$AFTER_FREE" >> "$LOG_FILE"
FINISHED_AT="$(now_iso)"
write_action_receipt mail_cache_remove "$STATUS" "$STARTED_AT" "$FINISHED_AT" "$LOG_FILE" >/dev/null
[ "$STATUS" = success ] || exit 1
