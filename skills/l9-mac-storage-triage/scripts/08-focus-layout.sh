#!/bin/bash
# l9-mac-storage-triage / scripts/08-focus-layout.sh
# purpose: bounded read-only sizes for home top-level, Library children, and Data-outside-home
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
require_macos
require_diagnosis

REPORT_DIR="$(latest_report_dir_from_state)"
TIMEOUT_SECONDS="${COMMAND_TIMEOUT_SECONDS:-40}"
OUT="$REPORT_DIR/focus-layout.tsv"
MD="$REPORT_DIR/focus-layout.md"

run_limited() {
  local seconds="$1"
  shift
  perl -e 'alarm shift; exec @ARGV' "$seconds" "$@"
}

size_one() {
  local path="$1"
  local class="$2"
  if [ ! -e "$path" ]; then
    printf 'MISSING\t0\t%s\t%s\n' "$class" "$path"
    return 0
  fi
  local kib
  kib="$(run_limited "$TIMEOUT_SECONDS" du -sk "$path" 2>/dev/null | awk '{print $1}' || true)"
  kib="$(printf '%s\n' "$kib" | awk 'NF{print $1; exit}')"
  if [ -z "${kib:-}" ]; then
    printf 'TIMEOUT_OR_DENIED\t0\t%s\t%s\n' "$class" "$path"
    return 0
  fi
  printf 'OK\t%s\t%s\t%s\n' "$kib" "$class" "$path"
}

skip_path() {
  case "$1" in
    "$HOME/Library/CloudStorage"|"$HOME/Library/CloudStorage"/*) return 0 ;;
    "$HOME/.Trash"|"$HOME/.Trash"/*) return 0 ;;
    *) return 1 ;;
  esac
}

log "Collecting bounded focus layout (read-only; CloudStorage skipped)"
{
  printf 'status\tkib\tclass\tpath\n'
  # Do not du $HOME as a whole (includes CloudStorage). Operator-provided home total is recorded in the ledger.
  # Immediate children of home, except Library (broken down below).
  while IFS= read -r -d '' path; do
    skip_path "$path" && continue
    [ "$path" = "$HOME/Library" ] && continue
    size_one "$path" home_child
  done < <(find "$HOME" -mindepth 1 -maxdepth 1 -print0 2>/dev/null)

  if [ -d "$HOME/Library" ]; then
    while IFS= read -r -d '' path; do
      skip_path "$path" && continue
      size_one "$path" library_child
    done < <(find "$HOME/Library" -mindepth 1 -maxdepth 1 -print0 2>/dev/null)
  fi

  for path in \
    "$HOME/miniconda3" \
    "$HOME/miniconda3/pkgs" \
    "$HOME/miniconda3/envs" \
    "$HOME/.npm" \
    "$HOME/.cursor" \
    "$HOME/.docker" \
    "$HOME/Library/Caches" \
    "$HOME/Library/Logs" \
    /opt/homebrew \
    /usr/local \
    /Applications \
    /Library \
    /private/var \
    /Users
  do
    size_one "$path" data_focus
  done
} > "$OUT"

{
  printf '# Focus layout (read-only)\n\n'
  printf 'CloudStorage and Trash were skipped. TIMEOUT_OR_DENIED means Unknown, not zero.\n\n'
  printf '| Status | GiB | Class | Path |\n'
  printf '|---|---:|---|---|\n'
  awk -F'\t' 'NR>1 {
    gib = $2/1048576
    printf "| %s | %.2f | %s | `%s` |\n", $1, gib, $3, $4
  }' "$OUT" | sort -t'|' -k3 -nr
} > "$MD"

printf '%s\n' "$OUT" > "$(state_dir)/focus-layout-path"
log "Focus layout written: $MD"
