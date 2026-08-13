#!/bin/bash
# l9-mac-storage-triage / scripts/actions/docker-prune-unused.sh
# purpose: prune stopped docker containers, dangling images, and build cache — never volumes
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
load_env
list_has_action docker_prune_unused || die "docker_prune_unused is not approved."
is_true "${DOCKER_PRUNE_UNUSED_APPROVED:-false}" || die "DOCKER_PRUNE_UNUSED_APPROVED must be true."
command -v docker >/dev/null 2>&1 || die "docker is not installed."
docker info >/dev/null 2>&1 || die "Docker daemon is not running."

STARTED_AT="$(now_iso)"
REPORT_DIR="$(latest_report_dir_from_state)"
mkdir -p "$REPORT_DIR/actions"
LOG_FILE="$REPORT_DIR/actions/docker-prune-unused.log"
BEFORE_FREE="$(free_kib_for_path "$DATA_VOLUME")"
STATUS=success
: > "$LOG_FILE"

run_logged() {
  local label="$1"
  shift
  printf 'BEGIN %s\n' "$label" >> "$LOG_FILE"
  if "$@" >>"$LOG_FILE" 2>&1; then
    printf 'OK %s\n' "$label" >> "$LOG_FILE"
  else
    printf 'FAIL %s\n' "$label" >> "$LOG_FILE"
    STATUS=fail
  fi
}

run_logged container_prune docker container prune -f
run_logged image_prune_dangling docker image prune -f
run_logged builder_prune docker builder prune -f
printf 'SKIP volumes — not allowlisted\n' >> "$LOG_FILE"
printf 'SKIP unused-named-image sweep — not allowlisted\n' >> "$LOG_FILE"

AFTER_FREE="$(free_kib_for_path "$DATA_VOLUME")"
printf 'free_kib_before=%s\nfree_kib_after=%s\n' "$BEFORE_FREE" "$AFTER_FREE" >> "$LOG_FILE"
FINISHED_AT="$(now_iso)"
write_action_receipt docker_prune_unused "$STATUS" "$STARTED_AT" "$FINISHED_AT" "$LOG_FILE" >/dev/null
[ "$STATUS" = success ] || exit 1
