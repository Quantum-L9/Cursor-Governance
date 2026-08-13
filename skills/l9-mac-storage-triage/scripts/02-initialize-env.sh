#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
require_macos
require_diagnosis
[ ! -e "$ROOT_DIR/.env" ] || die ".env already exists. Edit it directly or remove it intentionally before reinitializing."

REPORT_DIR="$(latest_report_dir_from_state)"
. "$REPORT_DIR/diagnosis.env"
SCAN_OUTPUT='UNKNOWN'
if [ -s "$(state_dir)/latest-ncdu-scan" ]; then SCAN_OUTPUT="$(cat "$(state_dir)/latest-ncdu-scan")"; fi

cat > "$ROOT_DIR/.env" <<EOF_ENV
TRIAGE_VERSION='1.0.0'
MAC_USER='$(id -un)'
HOME_DIR='$HOME'
HOST_NAME='$HOST_NAME'
DATA_VOLUME='$DATA_VOLUME'
REPORT_ROOT='$ROOT_DIR/reports'
STATE_DIR='$ROOT_DIR/.state'
DIAGNOSIS_RECEIPT='$ROOT_DIR/.state/diagnosis.complete'
LATEST_REPORT_DIR='$REPORT_DIR'
SCAN_ROOT='$HOME'
SCAN_OUTPUT_FILE='$SCAN_OUTPUT'
SCAN_EXCLUDE_FILE='$ROOT_DIR/config/scan-excludes.txt'
SCAN_ENGINE='ncdu'
SCAN_CROSS_FILESYSTEMS='false'
SCAN_SAVE_FOR_REUSE='true'
COMMAND_TIMEOUT_SECONDS='20'
MIN_FREE_GIB_FOR_REINDEX='30'
SPOTLIGHT_EXCLUSIONS_FILE='$ROOT_DIR/config/spotlight-exclusions.txt'
SPOTLIGHT_REINDEX_MODE='privacy_gui'
SPOTLIGHT_REINDEX_APPROVED='false'
TIME_MACHINE_EXCLUSIONS_FILE='$ROOT_DIR/config/time-machine-exclusions.txt'
MAIL_DATA_PATH='$HOME/Library/Mail'
MAIL_CACHE_REMOVE_APPROVED='false'
MAIL_SERVER_BACKED_CONFIRMED='UNKNOWN'
MAIL_LOCAL_ONLY_MAILBOXES_CONFIRMED_ABSENT='UNKNOWN'
OFFLOAD_SOURCE='UNKNOWN'
RCLONE_REMOTE='UNKNOWN'
RCLONE_REMOTE_PATH='UNKNOWN'
RCLONE_TRANSFERS='4'
RCLONE_CHECKERS='8'
OFFLOAD_APPROVED='false'
DELETE_OFFLOADED_SOURCE_APPROVED='false'
OFFLOAD_VERIFICATION_RECEIPT='UNKNOWN'
APPROVED_ACTIONS='UNKNOWN'
TRIAGE_MODE='diagnose'
PURGE_STALE_CACHES_APPROVED='false'
DOCKER_PRUNE_UNUSED_APPROVED='false'
EMPTY_TRASH_APPROVED='false'
XCODE_DERIVED_PURGE='false'
APPLY_CONFIRMATION='NOT_APPROVED'
AUTONOMY_CONFIRMATION='NOT_AUTHORIZED'
EOF_ENV
chmod 600 "$ROOT_DIR/.env"
log "Created $ROOT_DIR/.env with detected system values and explicit UNKNOWN decisions."
printf 'Edit .env and referenced config files, then run: ./bin/mac-storage-triage validate\n'
