#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
require_macos
require_diagnosis
load_env

FAILURES=0
fail() { printf 'FAIL: %s\n' "$*" >&2; FAILURES=$((FAILURES+1)); }
pass() { printf 'PASS: %s\n' "$*"; }

[ "$HOME_DIR" = "$HOME" ] && pass "HOME_DIR matches current user" || fail "HOME_DIR does not match current user"
[ -d "$DATA_VOLUME" ] && pass "DATA_VOLUME exists" || fail "DATA_VOLUME does not exist"
[ -f "$DIAGNOSIS_RECEIPT" ] && pass "diagnosis receipt exists" || fail "diagnosis receipt missing"
[ -d "$LATEST_REPORT_DIR" ] && pass "latest report directory exists" || fail "latest report directory missing"

if is_unknown "${APPROVED_ACTIONS:-UNKNOWN}"; then
  fail "APPROVED_ACTIONS is UNKNOWN"
else
  IFS=',' read -r -a actions <<< "$APPROVED_ACTIONS"
  for action in "${actions[@]}"; do
    case "$action" in
      spotlight_exclusions|spotlight_reindex_prepare|mail_cache_remove|offload_rclone|delete_verified_source|purge_stale_caches|docker_prune_unused|empty_trash) pass "supported action: $action" ;;
      *) fail "unsupported action: $action" ;;
    esac
  done
fi

if list_has_action spotlight_exclusions; then
  [ -f "$SPOTLIGHT_EXCLUSIONS_FILE" ] || fail "SPOTLIGHT_EXCLUSIONS_FILE missing"
  grep -Ev '^[[:space:]]*$|^[[:space:]]*#' "$SPOTLIGHT_EXCLUSIONS_FILE" >/dev/null 2>&1 || fail "Spotlight exclusion list has no paths"
fi

if list_has_action spotlight_reindex_prepare; then
  [ "$SPOTLIGHT_REINDEX_MODE" = "privacy_gui" ] || fail "Only privacy_gui reindex mode is supported by this release"
  is_true "$SPOTLIGHT_REINDEX_APPROVED" || fail "SPOTLIGHT_REINDEX_APPROVED must be true"
fi

if list_has_action mail_cache_remove; then
  require_absolute_path "$MAIL_DATA_PATH" "MAIL_DATA_PATH"
  case "$MAIL_DATA_PATH" in "$HOME/Library/Mail"|"$HOME/Library/Mail"/*) ;; *) fail "MAIL_DATA_PATH must remain inside the current user's Mail directory" ;; esac
  [ -d "$MAIL_DATA_PATH" ] || fail "MAIL_DATA_PATH does not exist"
  is_true "$MAIL_CACHE_REMOVE_APPROVED" || fail "MAIL_CACHE_REMOVE_APPROVED must be true"
  [ "$MAIL_SERVER_BACKED_CONFIRMED" = "true" ] || fail "MAIL_SERVER_BACKED_CONFIRMED must be true"
  [ "$MAIL_LOCAL_ONLY_MAILBOXES_CONFIRMED_ABSENT" = "true" ] || fail "MAIL_LOCAL_ONLY_MAILBOXES_CONFIRMED_ABSENT must be true"
fi

if list_has_action offload_rclone; then
  require_existing_dir "$OFFLOAD_SOURCE" "OFFLOAD_SOURCE"
  require_known RCLONE_REMOTE
  require_known RCLONE_REMOTE_PATH
  is_true "$OFFLOAD_APPROVED" || fail "OFFLOAD_APPROVED must be true"
  command -v rclone >/dev/null 2>&1 || fail "rclone is not installed"
  if command -v rclone >/dev/null 2>&1; then
    rclone listremotes 2>/dev/null | grep -Fx "${RCLONE_REMOTE}:" >/dev/null 2>&1 || fail "Configured rclone remote is not available: $RCLONE_REMOTE"
  fi
fi

if list_has_action delete_verified_source; then
  require_existing_dir "$OFFLOAD_SOURCE" "OFFLOAD_SOURCE"
  require_known OFFLOAD_VERIFICATION_RECEIPT
  [ -f "$OFFLOAD_VERIFICATION_RECEIPT" ] || fail "OFFLOAD_VERIFICATION_RECEIPT does not exist"
  is_true "$DELETE_OFFLOADED_SOURCE_APPROVED" || fail "DELETE_OFFLOADED_SOURCE_APPROVED must be true"
fi

if list_has_action purge_stale_caches; then
  is_true "${PURGE_STALE_CACHES_APPROVED:-false}" || fail "PURGE_STALE_CACHES_APPROVED must be true"
fi

if list_has_action docker_prune_unused; then
  is_true "${DOCKER_PRUNE_UNUSED_APPROVED:-false}" || fail "DOCKER_PRUNE_UNUSED_APPROVED must be true"
  command -v docker >/dev/null 2>&1 || fail "docker is not installed"
fi

if list_has_action empty_trash; then
  is_true "${EMPTY_TRASH_APPROVED:-false}" || fail "EMPTY_TRASH_APPROVED must be true"
  [ -d "$HOME/.Trash" ] || fail "Trash directory is missing"
fi

if [ "${TRIAGE_MODE:-}" = autonomy ]; then
  [ "${AUTONOMY_CONFIRMATION:-}" = "I_AUTHORIZE_SAFE_NOISE_PURGE" ] || fail "AUTONOMY_CONFIRMATION must equal I_AUTHORIZE_SAFE_NOISE_PURGE in autonomy mode"
  IFS=',' read -r -a autonomy_actions <<< "$APPROVED_ACTIONS"
  for action in "${autonomy_actions[@]}"; do
    is_safe_noise_action "$action" || fail "autonomy mode cannot include non-allowlisted action: $action"
  done
fi

if [ "${TRIAGE_MODE:-}" = repair ]; then
  [ "${AUTONOMY_CONFIRMATION:-NOT_AUTHORIZED}" = "NOT_AUTHORIZED" ] || fail "repair mode must not set AUTONOMY_CONFIRMATION"
fi

if [ "$FAILURES" -gt 0 ]; then
  printf 'Validation failed with %s blocking issue(s).\n' "$FAILURES" >&2
  exit 1
fi

VALIDATION_RECEIPT="$(state_dir)/env-validation.complete"
{
  printf "VALIDATED_AT='%s'\n" "$(now_iso)"
  printf "ENV_SHA256='%s'\n" "$(sha256_file "$ENV_FILE")"
  printf "APPROVED_ACTIONS='%s'\n" "$APPROVED_ACTIONS"
} > "$VALIDATION_RECEIPT"
pass "environment validation complete"
printf 'Next: ./bin/mac-storage-triage plan\n'
