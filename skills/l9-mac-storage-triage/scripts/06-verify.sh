#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
require_macos
require_diagnosis
require_plan
load_env
REPORT_DIR="$(latest_report_dir_from_state)"
. "$(state_dir)/diagnosis.env"
PLAN_SHA="$(cat "$(state_dir)/approved-plan.sha256")"
VERIFY_FILE="$REPORT_DIR/verification-report.md"
CURRENT_FREE="$(free_kib_for_path "$DATA_VOLUME")"
OVERALL=verified

{
  printf '# Verification Report\n\n'
  printf -- '- Plan SHA-256: `%s`\n' "$PLAN_SHA"
  printf -- '- Free KiB before: %s\n' "$FREE_KIB"
  printf -- '- Free KiB after: %s\n' "$CURRENT_FREE"
  printf -- '- Free KiB delta: %s\n\n' "$((CURRENT_FREE-FREE_KIB))"
  printf '## Action results\n\n'

  IFS=',' read -r -a actions <<< "$APPROVED_ACTIONS"
  for action in "${actions[@]}"; do
    receipt="$REPORT_DIR/receipts/${action}.env"
    if [ ! -f "$receipt" ]; then
      printf -- '- `%s`: Unknown; execution receipt missing.\n' "$action"
      OVERALL=partial
      continue
    fi
    status="$(awk -F"'" '/^STATUS=/{print $2}' "$receipt")"
    case "$action" in
      spotlight_exclusions)
        missing=0
        while IFS= read -r path; do
          case "$path" in ''|'#'*) continue ;; esac
          if cloudstorage_path "$path"; then continue; fi
          [ -f "$path/.metadata_never_index" ] || missing=$((missing+1))
        done < "$SPOTLIGHT_EXCLUSIONS_FILE"
        if [ "$status" = success ] && [ "$missing" -eq 0 ]; then
          printf -- '- `spotlight_exclusions`: verified; supported local markers exist.\n'
        else
          printf -- '- `spotlight_exclusions`: failed; missing markers or failed receipt.\n'
          OVERALL=failed
        fi
        ;;
      spotlight_reindex_prepare)
        printf -- '- `spotlight_reindex_prepare`: Unknown; preparation receipt exists, but Finder and Spotlight result quality requires operator testing after indexing completes.\n'
        [ "$OVERALL" = failed ] || OVERALL=partial
        ;;
      mail_cache_remove)
        if [ "$status" = success ] && [ ! -e "$MAIL_DATA_PATH" ]; then
          printf -- '- `mail_cache_remove`: verified; primary Mail data path is absent.\n'
        else
          printf -- '- `mail_cache_remove`: failed; path remains or receipt failed.\n'
          OVERALL=failed
        fi
        ;;
      offload_rclone)
        if [ -f "$REPORT_DIR/offload-verification.env" ] && grep -q "^STATUS='success'" "$REPORT_DIR/offload-verification.env"; then
          printf -- '- `offload_rclone`: verified by rclone check receipt; local source intentionally remains.\n'
        else
          printf -- '- `offload_rclone`: failed or verification receipt missing.\n'
          OVERALL=failed
        fi
        ;;
      delete_verified_source)
        if [ "$status" = success ] && [ ! -e "$OFFLOAD_SOURCE" ]; then
          printf -- '- `delete_verified_source`: verified; configured source is absent.\n'
        else
          printf -- '- `delete_verified_source`: failed; source remains or receipt failed.\n'
          OVERALL=failed
        fi
        ;;
      purge_stale_caches|docker_prune_unused|empty_trash)
        if [ "$status" = success ]; then
          printf -- '- `%s`: verified by execution receipt; free-space delta recorded.\n' "$action"
        else
          printf -- '- `%s`: failed receipt.\n' "$action"
          OVERALL=failed
        fi
        ;;
    esac
  done
  printf '\n## Overall status\n\n%s\n' "$OVERALL"
} > "$VERIFY_FILE"

printf "VERIFIED_AT='%s'\nPLAN_SHA256='%s'\nFREE_KIB_BEFORE='%s'\nFREE_KIB_AFTER='%s'\nOVERALL_STATUS='%s'\nREPORT='%s'\n" \
  "$(now_iso)" "$PLAN_SHA" "$FREE_KIB" "$CURRENT_FREE" "$OVERALL" "$VERIFY_FILE" > "$(state_dir)/verification.complete"
log "Verification report written: $VERIFY_FILE"
