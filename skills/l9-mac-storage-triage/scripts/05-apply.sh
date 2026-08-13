#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
require_macos
require_diagnosis
require_plan
load_env
[ "$APPLY_CONFIRMATION" = "I_APPROVE_THIS_PLAN" ] || die "APPLY_CONFIRMATION must equal I_APPROVE_THIS_PLAN after plan review."
if [ "${TRIAGE_MODE:-}" = autonomy ]; then
  [ "${AUTONOMY_CONFIRMATION:-}" = "I_AUTHORIZE_SAFE_NOISE_PURGE" ] || die "AUTONOMY_CONFIRMATION must equal I_AUTHORIZE_SAFE_NOISE_PURGE in autonomy mode."
fi
[ -f "$(state_dir)/env-validation.complete" ] || die "Environment validation receipt missing."
CURRENT_ENV_SHA="$(sha256_file "$ENV_FILE")"
VALIDATED_ENV_SHA="$(awk -F"'" '/^ENV_SHA256=/{print $2}' "$(state_dir)/env-validation.complete")"
[ "$CURRENT_ENV_SHA" = "$VALIDATED_ENV_SHA" ] || die "Environment changed after validation. Rerun validation."
CURRENT_CONFIG_SHA="$(plan_config_digest)"
APPROVED_CONFIG_SHA="$(cat "$(state_dir)/approved-config.sha256")"
[ "$CURRENT_CONFIG_SHA" = "$APPROVED_CONFIG_SHA" ] || die "Action configuration changed after plan generation. Regenerate the plan."
PLAN_PATH="$(cat "$(state_dir)/approved-plan-path")"
CURRENT_PLAN_SHA="$(sha256_file "$PLAN_PATH")"
APPROVED_PLAN_SHA="$(cat "$(state_dir)/approved-plan.sha256")"
[ "$CURRENT_PLAN_SHA" = "$APPROVED_PLAN_SHA" ] || die "Approved plan file changed after generation."

log "Executing only approved actions from plan $APPROVED_PLAN_SHA"
IFS=',' read -r -a actions <<< "$APPROVED_ACTIONS"
for action in "${actions[@]}"; do
  case "$action" in
    spotlight_exclusions) "$ROOT_DIR/scripts/actions/spotlight-exclusions.sh" ;;
    spotlight_reindex_prepare) "$ROOT_DIR/scripts/actions/spotlight-reindex-prepare.sh" ;;
    mail_cache_remove) "$ROOT_DIR/scripts/actions/mail-cache-remove.sh" ;;
    offload_rclone) "$ROOT_DIR/scripts/actions/offload-rclone.sh" ;;
    delete_verified_source) "$ROOT_DIR/scripts/actions/delete-verified-source.sh" ;;
    purge_stale_caches) "$ROOT_DIR/scripts/actions/purge-stale-caches.sh" ;;
    docker_prune_unused) "$ROOT_DIR/scripts/actions/docker-prune-unused.sh" ;;
    empty_trash) "$ROOT_DIR/scripts/actions/empty-trash.sh" ;;
    *) die "Unsupported planned action: $action" ;;
  esac
done
printf "APPLIED_AT='%s'\nPLAN_SHA256='%s'\n" "$(now_iso)" "$APPROVED_PLAN_SHA" > "$(state_dir)/apply.complete"
log "Approved actions completed."
printf 'Next: ./bin/mac-storage-triage verify\n'
