#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
load_env
list_has_action spotlight_reindex_prepare || die "spotlight_reindex_prepare is not approved."
is_true "$SPOTLIGHT_REINDEX_APPROVED" || die "Spotlight reindex preparation is not approved."
STARTED_AT="$(now_iso)"
REPORT_DIR="$(latest_report_dir_from_state)"
LOG_FILE="$REPORT_DIR/actions/spotlight-reindex-prepare.log"
mkdir -p "$REPORT_DIR/actions"

FREE_KIB="$(free_kib_for_path "$DATA_VOLUME")"
FREE_GIB="$(awk -v k="$FREE_KIB" 'BEGIN {printf "%.1f", k/1048576}')"
awk -v free="$FREE_GIB" -v min="$MIN_FREE_GIB_FOR_REINDEX" 'BEGIN {exit !(free >= min)}' || die "Only $FREE_GIB GiB is free; at least $MIN_FREE_GIB_FOR_REINDEX GiB is required before reindex preparation."

{
  printf 'free_gib=%s\n' "$FREE_GIB"
  printf 'required_free_gib=%s\n' "$MIN_FREE_GIB_FOR_REINDEX"
  printf 'mode=%s\n' "$SPOTLIGHT_REINDEX_MODE"
  printf 'spotlight_state_begin\n'
  run_with_timeout "$COMMAND_TIMEOUT_SECONDS" mdutil -sa 2>&1 || true
  printf 'spotlight_state_end\n'
  printf 'procedure=Add HOME_DIR to Spotlight Search Privacy, wait 30 seconds, remove HOME_DIR, keep cloud-provider roots excluded, then leave the Mac awake.\n'
} > "$LOG_FILE"

open -a "System Settings" >/dev/null 2>&1 || true
FINISHED_AT="$(now_iso)"
write_action_receipt spotlight_reindex_prepare success "$STARTED_AT" "$FINISHED_AT" "$LOG_FILE" >/dev/null
printf 'System Settings opened. Complete the Search Privacy add-wait-remove procedure for: %s\n' "$HOME_DIR"
