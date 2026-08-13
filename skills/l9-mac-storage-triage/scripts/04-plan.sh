#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
require_macos
require_diagnosis
load_env
[ -f "$(state_dir)/env-validation.complete" ] || die "Environment validation receipt missing."
CURRENT_ENV_SHA="$(sha256_file "$ENV_FILE")"
VALIDATED_ENV_SHA="$(awk -F"'" '/^ENV_SHA256=/{print $2}' "$(state_dir)/env-validation.complete")"
[ "$CURRENT_ENV_SHA" = "$VALIDATED_ENV_SHA" ] || die "Environment changed after validation. Rerun validation."

REPORT_DIR="$(latest_report_dir_from_state)"
PLAN="$REPORT_DIR/remediation-plan.md"
PLAN_ID="plan-$(now_compact)"
{
  printf '# Remediation Plan\n\n'
  printf -- '- Plan ID: `%s`\n' "$PLAN_ID"
  printf -- '- Diagnosis receipt: `%s`\n' "$DIAGNOSIS_RECEIPT"
  printf -- '- Environment digest: `%s`\n' "$CURRENT_ENV_SHA"
  printf -- '- Approval required: true\n\n'
  printf '## Approved changes\n\n'
  IFS=',' read -r -a actions <<< "$APPROVED_ACTIONS"
  for action in "${actions[@]}"; do
    case "$action" in
      spotlight_exclusions)
        printf '### spotlight_exclusions\n\n'
        printf -- '- Target source: `%s`\n' "$SPOTLIGHT_EXCLUSIONS_FILE"
        printf -- '- Old state: listed paths may be indexed or require manual File Provider privacy configuration.\n'
        printf -- '- New state: ordinary local directories receive `.metadata_never_index`; File Provider paths are listed for manual Search Privacy handling.\n'
        printf -- '- Guard: each target must exist and resolve to an absolute path.\n'
        printf -- '- Verification: marker presence or manual-path receipt.\n\n'
        ;;
      spotlight_reindex_prepare)
        printf '### spotlight_reindex_prepare\n\n'
        printf -- '- Target: `%s`\n' "$HOME_DIR"
        printf -- '- Old state: Spotlight state may be stale or Unknown.\n'
        printf -- '- New state: prerequisites checked and System Settings opened for a home-folder privacy-toggle rebuild.\n'
        printf -- '- Guard: at least %s GiB free; no automated `mdutil -E` execution.\n' "$MIN_FREE_GIB_FOR_REINDEX"
        printf -- '- Verification: known local files and applications return in targeted searches.\n\n'
        ;;
      mail_cache_remove)
        printf '### mail_cache_remove\n\n'
        printf -- '- Target: `%s`\n' "$MAIL_DATA_PATH"
        printf -- '- Old state: local Apple Mail data exists.\n'
        printf -- '- New state: current-user Mail store, caches, preferences, and saved state are removed.\n'
        printf -- '- Guard: server-backed status and absence of local-only mailboxes are explicitly confirmed.\n'
        printf -- '- Verification: target paths absent and free-space delta recorded.\n\n'
        ;;
      offload_rclone)
        printf '### offload_rclone\n\n'
        printf -- '- Source: `%s`\n' "$OFFLOAD_SOURCE"
        printf -- '- Destination: `%s:%s`\n' "$RCLONE_REMOTE" "$RCLONE_REMOTE_PATH"
        printf -- '- Old state: source exists only on local disk or lacks verified remote copy.\n'
        printf -- '- New state: source is streamed to the configured remote and checked without creating a second local copy.\n'
        printf -- '- Guard: configured remote exists and source remains unchanged during transfer.\n'
        printf -- '- Verification: `rclone check` succeeds and a verification receipt is written.\n\n'
        ;;
      delete_verified_source)
        printf '### delete_verified_source\n\n'
        printf -- '- Target: `%s`\n' "$OFFLOAD_SOURCE"
        printf -- '- Old state: verified source remains local after cloud offload.\n'
        printf -- '- New state: verified local source is permanently removed.\n'
        printf -- '- Guard: matching successful offload receipt and explicit deletion approval.\n'
        printf -- '- Verification: source path absent and free-space delta recorded.\n\n'
        ;;
      purge_stale_caches)
        printf '### purge_stale_caches\n\n'
        printf -- '- Target: Homebrew cache dir (`~/Library/Caches/Homebrew` only — not brew cleanup), npm/yarn/pnpm, pip, conda package caches (`conda clean`, not rm pkgs), uv cache, and Chrome disk cache (`~/Library/Caches/Google` only).\n'
        printf -- '- Old state: regenerating package-manager and browser caches occupy local disk.\n'
        printf -- '- New state: those caches are purged; conda environments and Chrome Application Support are kept.\n'
        printf -- '- Guard: Xcode DerivedData is skipped unless XCODE_DERIVED_PURGE=true. Never wipe `~/Library/Caches` wholesale.\n'
        printf -- '- Verification: action receipt and free-space delta.\n\n'
        ;;
      docker_prune_unused)
        printf '### docker_prune_unused\n\n'
        printf -- '- Target: stopped Docker containers, dangling images, build cache.\n'
        printf -- '- Old state: unused Docker artifacts occupy local disk.\n'
        printf -- '- New state: stopped containers and dangling images/build cache are removed.\n'
        printf -- '- Guard: volumes and named in-use images are not pruned.\n'
        printf -- '- Verification: action receipt and free-space delta.\n\n'
        ;;
      empty_trash)
        printf '### empty_trash\n\n'
        printf -- '- Target: `%s/.Trash`\n' "$HOME_DIR"
        printf -- '- Old state: user Trash holds deleted files.\n'
        printf -- '- New state: Trash is empty.\n'
        printf -- '- Guard: only the current user Trash path is touched.\n'
        printf -- '- Verification: action receipt and free-space delta.\n\n'
        ;;
    esac
  done
} > "$PLAN"
PLAN_SHA="$(sha256_file "$PLAN")"
CONFIG_SHA="$(plan_config_digest)"
printf '%s\n' "$PLAN_SHA" > "$(state_dir)/approved-plan.sha256"
printf '%s\n' "$CONFIG_SHA" > "$(state_dir)/approved-config.sha256"
printf '%s\n' "$PLAN" > "$(state_dir)/approved-plan-path"
printf "PLAN_ID='%s'\nPLAN_SHA256='%s'\nCONFIG_SHA256='%s'\nPLAN_PATH='%s'\n" "$PLAN_ID" "$PLAN_SHA" "$CONFIG_SHA" "$PLAN" > "$(state_dir)/approved-plan.env"
log "Plan generated: $PLAN"
printf 'Review it, set APPLY_CONFIRMATION to I_APPROVE_THIS_PLAN, rerun validate, then run apply.\n'
