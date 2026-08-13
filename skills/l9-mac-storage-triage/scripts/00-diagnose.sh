#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/common.sh
. "$ROOT_DIR/scripts/lib/common.sh"
require_macos

STATE_DIR="$ROOT_DIR/.state"
mkdir -p "$STATE_DIR" "$ROOT_DIR/reports"
DATA_VOLUME="$(data_volume_detect)"
REPORT_ID="$(now_compact)-$(scutil --get LocalHostName 2>/dev/null || hostname -s)"
REPORT_DIR="$ROOT_DIR/reports/$REPORT_ID"
mkdir -p "$REPORT_DIR"
TIMEOUT_SECONDS=20

log "Collecting read-only system evidence in $REPORT_DIR"
{
  df -h / 2>&1
  [ "$DATA_VOLUME" = "/" ] || df -h "$DATA_VOLUME" 2>&1
} > "$REPORT_DIR/df.txt"

diskutil info / > "$REPORT_DIR/diskutil-root.txt" 2>&1 || true
if diskutil apfs list > "$REPORT_DIR/apfs.txt" 2>&1; then :; else printf 'APFS inventory unavailable.\n' > "$REPORT_DIR/apfs.txt"; fi
run_with_timeout "$TIMEOUT_SECONDS" tmutil listlocalsnapshots / > "$REPORT_DIR/snapshots.txt" 2>&1 || printf 'Snapshot query failed or timed out.\n' >> "$REPORT_DIR/snapshots.txt"
run_with_timeout 10 mdutil -sa > "$REPORT_DIR/spotlight-state.txt" 2>&1 || printf 'Spotlight state query failed or timed out.\n' >> "$REPORT_DIR/spotlight-state.txt"

{
  printf 'macOS_version=%s\n' "$(sw_vers -productVersion)"
  printf 'macOS_build=%s\n' "$(sw_vers -buildVersion)"
  printf 'architecture=%s\n' "$(uname -m)"
  printf 'host_name=%s\n' "$(scutil --get LocalHostName 2>/dev/null || hostname -s)"
  printf 'home_dir=%s\n' "$HOME"
  printf 'data_volume=%s\n' "$DATA_VOLUME"
  printf 'free_kib=%s\n' "$(free_kib_for_path "$DATA_VOLUME")"
  printf 'used_kib=%s\n' "$(used_kib_for_path "$DATA_VOLUME")"
  printf 'ncdu=%s\n' "$(command -v ncdu 2>/dev/null || printf 'MISSING')"
  printf 'rclone=%s\n' "$(command -v rclone 2>/dev/null || printf 'MISSING')"
  printf 'docker=%s\n' "$(command -v docker 2>/dev/null || printf 'MISSING')"
  printf 'conda=%s\n' "$(command -v conda 2>/dev/null || printf 'MISSING')"
} > "$REPORT_DIR/system-facts.txt"

{
  for path in \
    "$HOME/Library" \
    "$HOME/Library/Mail" \
    "$HOME/Library/CloudStorage" \
    "$HOME/Library/Containers" \
    "$HOME/Library/Application Support" \
    "$HOME/.local/share" \
    "$HOME/Downloads" \
    "$HOME/Documents"; do
    if [ -e "$path" ]; then
      ls -ldO@ "$path" 2>&1
    else
      printf 'MISSING %s\n' "$path"
    fi
  done
} > "$REPORT_DIR/path-presence.txt"

if command -v docker >/dev/null 2>&1; then
  run_with_timeout 15 docker system df > "$REPORT_DIR/docker-system-df.txt" 2>&1 || printf 'Docker query failed or timed out.\n' >> "$REPORT_DIR/docker-system-df.txt"
fi

if command -v conda >/dev/null 2>&1; then
  run_with_timeout 30 conda clean --all --dry-run > "$REPORT_DIR/conda-clean-dry-run.txt" 2>&1 || printf 'Conda dry run failed or timed out.\n' >> "$REPORT_DIR/conda-clean-dry-run.txt"
fi

FREE_KIB="$(free_kib_for_path "$DATA_VOLUME")"
USED_KIB="$(used_kib_for_path "$DATA_VOLUME")"
HOST_NAME="$(scutil --get LocalHostName 2>/dev/null || hostname -s)"
CREATED_AT="$(now_iso)"
cat > "$REPORT_DIR/diagnosis.env" <<EOF_ENV
REPORT_ID='$REPORT_ID'
CREATED_AT='$CREATED_AT'
HOST_NAME='$HOST_NAME'
HOME_DIR='$HOME'
DATA_VOLUME='$DATA_VOLUME'
FREE_KIB='$FREE_KIB'
USED_KIB='$USED_KIB'
REPORT_DIR='$REPORT_DIR'
DIAGNOSIS_COMPLETE='true'
EOF_ENV

cat > "$REPORT_DIR/diagnosis.md" <<EOF_MD
# macOS Storage Diagnosis

- Report: $REPORT_ID
- Created: $CREATED_AT
- Host: $HOST_NAME
- Home: $HOME
- Data volume: $DATA_VOLUME
- Free KiB: $FREE_KIB
- Used KiB: $USED_KIB
- Mode: read-only, non-recursive baseline

## Evidence

- df.txt
- diskutil-root.txt
- apfs.txt
- snapshots.txt
- spotlight-state.txt
- system-facts.txt
- path-presence.txt
EOF_MD

printf '%s\n' "$REPORT_DIR" > "$STATE_DIR/latest-report-dir"
cp "$REPORT_DIR/diagnosis.env" "$STATE_DIR/diagnosis.env"
printf "REPORT_ID='%s'\nREPORT_DIR='%s'\nCREATED_AT='%s'\n" "$REPORT_ID" "$REPORT_DIR" "$CREATED_AT" > "$STATE_DIR/diagnosis.complete"
log "Diagnosis complete. No write remediation was performed."
printf 'Next: ./bin/mac-storage-triage inventory  (or: ./bin/mac-storage-triage run diagnose)\n'
