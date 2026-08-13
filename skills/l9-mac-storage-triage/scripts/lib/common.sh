#!/bin/bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR must be set before loading common.sh}"
ENV_FILE="${MAC_STORAGE_TRIAGE_ENV:-$ROOT_DIR/.env}"

now_compact() { date '+%Y%m%dT%H%M%S'; }
now_iso() { date '+%Y-%m-%dT%H:%M:%S%z'; }
log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

require_macos() {
  [ "$(uname -s)" = "Darwin" ] || die "This playbook must run on macOS."
}

validate_env_syntax() {
  local file="$1"
  [ -f "$file" ] || die "Environment file not found: $file"
  if grep -nE '(^|[^#])(`|\$\(|;|&&|\|\||[<>])' "$file" >/dev/null 2>&1; then
    die "Unsafe shell syntax found in environment file: $file"
  fi
  if grep -nEv '^[[:space:]]*$|^[[:space:]]*#|^[A-Z][A-Z0-9_]*=' "$file" >/dev/null 2>&1; then
    die "Invalid environment assignment found in: $file"
  fi
}

load_env() {
  validate_env_syntax "$ENV_FILE"
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
}

is_true() { [ "${1:-false}" = "true" ]; }
is_unknown() { [ -z "${1:-}" ] || [ "${1:-}" = "UNKNOWN" ]; }

require_known() {
  local name="$1"
  local value="${!name:-UNKNOWN}"
  is_unknown "$value" && die "$name is UNKNOWN. Populate it from diagnosis evidence before continuing."
}

require_absolute_path() {
  local value="$1"
  local label="$2"
  case "$value" in
    /*) ;;
    *) die "$label must be an absolute path: $value" ;;
  esac
}

require_existing_dir() {
  local value="$1"
  local label="$2"
  require_absolute_path "$value" "$label"
  [ -d "$value" ] || die "$label is not an existing directory: $value"
}

require_safe_user_delete_path() {
  local value="$1"
  require_absolute_path "$value" "delete target"
  [ "$value" != "/" ] || die "Refusing to delete root."
  [ "$value" != "$HOME" ] || die "Refusing to delete the home directory."
  case "$value" in
    "$HOME"/*) ;;
    *) die "Refusing to delete a path outside the current home directory: $value" ;;
  esac
}

state_dir() {
  if [ -n "${STATE_DIR:-}" ] && [ "${STATE_DIR:-}" != "UNKNOWN" ]; then
    printf '%s\n' "$STATE_DIR"
  else
    printf '%s\n' "$ROOT_DIR/.state"
  fi
}

require_diagnosis() {
  local receipt="$(state_dir)/diagnosis.complete"
  [ -f "$receipt" ] || die "Diagnosis receipt missing. Run: ./bin/mac-storage-triage diagnose"
}

require_plan() {
  local plan="$(state_dir)/approved-plan.sha256"
  [ -s "$plan" ] || die "Approved plan digest missing. Run validation and plan generation first."
}

free_kib_for_path() {
  df -k "$1" | awk 'NR==2 {print $4}'
}

used_kib_for_path() {
  df -k "$1" | awk 'NR==2 {print $3}'
}

data_volume_detect() {
  if [ -d /System/Volumes/Data ] && mount | grep -q ' on /System/Volumes/Data '; then
    printf '%s\n' '/System/Volumes/Data'
  else
    printf '%s\n' '/'
  fi
}

run_with_timeout() {
  local seconds="$1"
  shift
  "$@" &
  local command_pid=$!
  (
    sleep "$seconds"
    kill -TERM "$command_pid" 2>/dev/null || true
    sleep 2
    kill -KILL "$command_pid" 2>/dev/null || true
  ) &
  local watcher_pid=$!
  local status=0
  wait "$command_pid" || status=$?
  kill "$watcher_pid" 2>/dev/null || true
  wait "$watcher_pid" 2>/dev/null || true
  return "$status"
}

latest_report_dir_from_state() {
  local pointer="$(state_dir)/latest-report-dir"
  [ -s "$pointer" ] || die "Latest report pointer missing. Run diagnosis first."
  cat "$pointer"
}

list_has_action() {
  local wanted="$1"
  local list=",${APPROVED_ACTIONS:-},"
  case "$list" in
    *",$wanted,"*) return 0 ;;
    *) return 1 ;;
  esac
}

write_action_receipt() {
  local action_id="$1"
  local status="$2"
  local started_at="$3"
  local finished_at="$4"
  local log_file="$5"
  local receipts_dir="$(latest_report_dir_from_state)/receipts"
  mkdir -p "$receipts_dir"
  local plan_sha
  plan_sha="$(cat "$(state_dir)/approved-plan.sha256")"
  local receipt="$receipts_dir/${action_id}.env"
  {
    printf "RECEIPT_ID='%s'\n" "receipt-$(now_compact)-$action_id"
    printf "ACTION_ID='%s'\n" "$action_id"
    printf "PLAN_SHA256='%s'\n" "$plan_sha"
    printf "STARTED_AT='%s'\n" "$started_at"
    printf "FINISHED_AT='%s'\n" "$finished_at"
    printf "STATUS='%s'\n" "$status"
    printf "LOG_FILE='%s'\n" "$log_file"
  } > "$receipt"
  printf '%s\n' "$receipt"
}


SAFE_NOISE_ACTIONS='purge_stale_caches,docker_prune_unused,empty_trash'

is_safe_noise_action() {
  case "$1" in
    purge_stale_caches|docker_prune_unused|empty_trash) return 0 ;;
    *) return 1 ;;
  esac
}

plan_config_digest() {
  {
    printf 'APPROVED_ACTIONS=%s\n' "${APPROVED_ACTIONS:-}"
    printf 'TRIAGE_MODE=%s\n' "${TRIAGE_MODE:-}"
    printf 'PURGE_STALE_CACHES_APPROVED=%s\n' "${PURGE_STALE_CACHES_APPROVED:-}"
    printf 'DOCKER_PRUNE_UNUSED_APPROVED=%s\n' "${DOCKER_PRUNE_UNUSED_APPROVED:-}"
    printf 'EMPTY_TRASH_APPROVED=%s\n' "${EMPTY_TRASH_APPROVED:-}"
    printf 'XCODE_DERIVED_PURGE=%s\n' "${XCODE_DERIVED_PURGE:-}"
    printf 'SPOTLIGHT_EXCLUSIONS_FILE=%s\n' "${SPOTLIGHT_EXCLUSIONS_FILE:-}"
    printf 'SPOTLIGHT_REINDEX_MODE=%s\n' "${SPOTLIGHT_REINDEX_MODE:-}"
    printf 'SPOTLIGHT_REINDEX_APPROVED=%s\n' "${SPOTLIGHT_REINDEX_APPROVED:-}"
    printf 'MIN_FREE_GIB_FOR_REINDEX=%s\n' "${MIN_FREE_GIB_FOR_REINDEX:-}"
    printf 'MAIL_DATA_PATH=%s\n' "${MAIL_DATA_PATH:-}"
    printf 'MAIL_CACHE_REMOVE_APPROVED=%s\n' "${MAIL_CACHE_REMOVE_APPROVED:-}"
    printf 'MAIL_SERVER_BACKED_CONFIRMED=%s\n' "${MAIL_SERVER_BACKED_CONFIRMED:-}"
    printf 'MAIL_LOCAL_ONLY_MAILBOXES_CONFIRMED_ABSENT=%s\n' "${MAIL_LOCAL_ONLY_MAILBOXES_CONFIRMED_ABSENT:-}"
    printf 'OFFLOAD_SOURCE=%s\n' "${OFFLOAD_SOURCE:-}"
    printf 'RCLONE_REMOTE=%s\n' "${RCLONE_REMOTE:-}"
    printf 'RCLONE_REMOTE_PATH=%s\n' "${RCLONE_REMOTE_PATH:-}"
    printf 'RCLONE_TRANSFERS=%s\n' "${RCLONE_TRANSFERS:-}"
    printf 'RCLONE_CHECKERS=%s\n' "${RCLONE_CHECKERS:-}"
    printf 'OFFLOAD_APPROVED=%s\n' "${OFFLOAD_APPROVED:-}"
    printf 'DELETE_OFFLOADED_SOURCE_APPROVED=%s\n' "${DELETE_OFFLOADED_SOURCE_APPROVED:-}"
    printf 'OFFLOAD_VERIFICATION_RECEIPT=%s\n' "${OFFLOAD_VERIFICATION_RECEIPT:-}"
  } | shasum -a 256 | awk '{print $1}'
}

sha256_file() {
  shasum -a 256 "$1" | awk '{print $1}'
}

cloudstorage_path() {
  case "$1" in
    "$HOME/Library/CloudStorage"|"$HOME/Library/CloudStorage"/*) return 0 ;;
    *) return 1 ;;
  esac
}
