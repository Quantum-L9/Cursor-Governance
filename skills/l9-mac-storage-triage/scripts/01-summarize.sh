#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
require_macos
require_diagnosis
REPORT_DIR="$(latest_report_dir_from_state)"
. "$REPORT_DIR/diagnosis.env"

USED_GIB="$(awk -v k="$USED_KIB" 'BEGIN {printf "%.1f", k/1048576}')"
FREE_GIB="$(awk -v k="$FREE_KIB" 'BEGIN {printf "%.1f", k/1048576}')"
SUMMARY="$REPORT_DIR/diagnosis-summary.md"

{
  printf '# Diagnosis Summary\n\n'
  printf -- '- Report ID: `%s`\n' "$REPORT_ID"
  printf -- '- Data volume: `%s`\n' "$DATA_VOLUME"
  printf -- '- Used: %s GiB\n' "$USED_GIB"
  printf -- '- Free: %s GiB\n' "$FREE_GIB"
  printf -- '- Write actions proposed: false\n\n'
  printf '## Confirmed baseline\n\n'
  printf -- '- APFS and filesystem evidence is stored in the report directory.\n'
  printf -- '- The baseline diagnosis did not recurse through user data.\n'
  printf -- '- Sparse-file logical sizes must not be treated as allocated sizes without a block-allocation check.\n'
  printf -- '- File Provider trees may reject hidden files and may stall recursive scanners.\n\n'
  if [ -f "$REPORT_DIR/noise-inventory.md" ]; then
    printf '## Noise inventory\n\n'
    cat "$REPORT_DIR/noise-inventory.md"
    printf '\n'
  fi
  if [ -f "$REPORT_DIR/focus-layout.md" ]; then
    printf '## Focus layout\n\n'
    cat "$REPORT_DIR/focus-layout.md"
    printf '\n'
  fi
  printf '## Classification queue\n\n'
  printf '| Path or category | Classification | Evidence status |\n'
  printf '|---|---|---|\n'
  printf '| Large local directories | Unknown | Requires targeted saved scan or operator evidence |\n'
  printf '| CloudStorage providers | cloud_managed_content | Presence evidence only |\n'
  printf '| Apple Mail local data | Unknown | Requires size and account-safety confirmation |\n'
  printf '| Large virtual disk files | apparent_sparse_allocation | Requires allocated-block inspection |\n'
  printf '| Spotlight health | Unknown | See `spotlight-state.txt` |\n\n'
  printf '## Next evidence action\n\n'
  printf 'Use `./bin/mac-storage-triage run repair` to plan allowlisted cache/docker/trash purge with HITL.\n'
} > "$SUMMARY"

printf '%s\n' "$SUMMARY" > "$(state_dir)/diagnosis-summary-path"
log "Summary written: $SUMMARY"
printf 'Next: ./bin/mac-storage-triage init-env\n'
