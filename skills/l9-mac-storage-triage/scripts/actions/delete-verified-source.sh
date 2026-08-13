#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
load_env
list_has_action delete_verified_source || die "delete_verified_source is not approved."
is_true "$DELETE_OFFLOADED_SOURCE_APPROVED" || die "Source deletion approval is false."
require_existing_dir "$OFFLOAD_SOURCE" "OFFLOAD_SOURCE"
require_safe_user_delete_path "$OFFLOAD_SOURCE"
require_known OFFLOAD_VERIFICATION_RECEIPT
[ -f "$OFFLOAD_VERIFICATION_RECEIPT" ] || die "Offload verification receipt not found."
validate_env_syntax "$OFFLOAD_VERIFICATION_RECEIPT"
set -a
. "$OFFLOAD_VERIFICATION_RECEIPT"
set +a
[ "$STATUS" = success ] || die "Offload verification receipt is not successful."
[ "$SOURCE" = "$OFFLOAD_SOURCE" ] || die "Receipt source does not match OFFLOAD_SOURCE."
[ "$DESTINATION" = "${RCLONE_REMOTE}:${RCLONE_REMOTE_PATH}" ] || die "Receipt destination does not match the configured remote."
command -v rclone >/dev/null 2>&1 || die "rclone is required for final pre-delete verification."

STARTED_AT="$(now_iso)"
REPORT_DIR="$(latest_report_dir_from_state)"
mkdir -p "$REPORT_DIR/actions"
LOG_FILE="$REPORT_DIR/actions/delete-verified-source.log"
BEFORE_FREE="$(free_kib_for_path "$DATA_VOLUME")"
rclone check "$OFFLOAD_SOURCE" "$DESTINATION" --one-way --log-level INFO --log-file "$LOG_FILE"
rm -rf "$OFFLOAD_SOURCE" >>"$LOG_FILE" 2>&1
[ ! -e "$OFFLOAD_SOURCE" ] || die "Source path remains after deletion."
AFTER_FREE="$(free_kib_for_path "$DATA_VOLUME")"
printf 'free_kib_before=%s\nfree_kib_after=%s\n' "$BEFORE_FREE" "$AFTER_FREE" >> "$LOG_FILE"
FINISHED_AT="$(now_iso)"
write_action_receipt delete_verified_source success "$STARTED_AT" "$FINISHED_AT" "$LOG_FILE" >/dev/null
