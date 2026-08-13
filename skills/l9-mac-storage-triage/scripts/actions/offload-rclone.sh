#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
load_env
list_has_action offload_rclone || die "offload_rclone is not approved."
is_true "$OFFLOAD_APPROVED" || die "Offload approval is false."
require_existing_dir "$OFFLOAD_SOURCE" "OFFLOAD_SOURCE"
require_known RCLONE_REMOTE
require_known RCLONE_REMOTE_PATH
command -v rclone >/dev/null 2>&1 || die "rclone is not installed."
rclone listremotes | grep -Fx "${RCLONE_REMOTE}:" >/dev/null || die "rclone remote not found: $RCLONE_REMOTE"

STARTED_AT="$(now_iso)"
REPORT_DIR="$(latest_report_dir_from_state)"
mkdir -p "$REPORT_DIR/actions"
LOG_FILE="$REPORT_DIR/actions/offload-rclone.log"
VERIFY_RECEIPT="$REPORT_DIR/offload-verification.env"
DESTINATION="${RCLONE_REMOTE}:${RCLONE_REMOTE_PATH}"
BEFORE_FREE="$(free_kib_for_path "$DATA_VOLUME")"

rclone size "$OFFLOAD_SOURCE" > "$REPORT_DIR/actions/offload-source-size.txt" 2>&1 || true
rclone copy "$OFFLOAD_SOURCE" "$DESTINATION" \
  --transfers "$RCLONE_TRANSFERS" \
  --checkers "$RCLONE_CHECKERS" \
  --create-empty-src-dirs \
  --stats 30s \
  --log-level INFO \
  --log-file "$LOG_FILE"

if rclone check "$OFFLOAD_SOURCE" "$DESTINATION" --one-way --log-level INFO --log-file "$LOG_FILE"; then
  CHECK_STATUS=success
else
  CHECK_STATUS=fail
fi
AFTER_FREE="$(free_kib_for_path "$DATA_VOLUME")"
cat > "$VERIFY_RECEIPT" <<EOF_RECEIPT
SOURCE='$OFFLOAD_SOURCE'
DESTINATION='$DESTINATION'
VERIFIED_AT='$(now_iso)'
STATUS='$CHECK_STATUS'
CHECK_LOG='$LOG_FILE'
FREE_KIB_BEFORE='$BEFORE_FREE'
FREE_KIB_AFTER='$AFTER_FREE'
EOF_RECEIPT
FINISHED_AT="$(now_iso)"
write_action_receipt offload_rclone "$CHECK_STATUS" "$STARTED_AT" "$FINISHED_AT" "$LOG_FILE" >/dev/null
printf 'Offload verification receipt: %s\n' "$VERIFY_RECEIPT"
[ "$CHECK_STATUS" = success ] || exit 1
