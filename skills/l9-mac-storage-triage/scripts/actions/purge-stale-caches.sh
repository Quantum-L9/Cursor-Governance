#!/bin/bash
# l9-mac-storage-triage / scripts/actions/purge-stale-caches.sh
# purpose: delete regenerating package-manager caches listed in the allowlist
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
load_env
list_has_action purge_stale_caches || die "purge_stale_caches is not approved."
is_true "${PURGE_STALE_CACHES_APPROVED:-false}" || die "PURGE_STALE_CACHES_APPROVED must be true."

STARTED_AT="$(now_iso)"
REPORT_DIR="$(latest_report_dir_from_state)"
mkdir -p "$REPORT_DIR/actions"
LOG_FILE="$REPORT_DIR/actions/purge-stale-caches.log"
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

# Cache directory only. `brew cleanup -s --prune=all` also removes
# /opt/homebrew/Library/Homebrew/vendor/portable-ruby (guarded Cellar/prefix).
if command -v brew >/dev/null 2>&1; then
  brew_cache="$(brew --cache)"
  case "$brew_cache" in
    "$HOME/Library/Caches/Homebrew") ;;
    *) die "brew --cache is not the allowlisted Homebrew cache: $brew_cache" ;;
  esac
  require_safe_user_delete_path "$brew_cache"
  if [ -e "$brew_cache" ]; then
    run_logged brew_cache rm -rf "$brew_cache"
  else
    printf 'SKIP brew_cache (absent)\n' >> "$LOG_FILE"
  fi
fi
if command -v npm >/dev/null 2>&1; then
  run_logged npm_cache npm cache clean --force
fi
if command -v yarn >/dev/null 2>&1; then
  run_logged yarn_cache yarn cache clean
fi
if command -v pnpm >/dev/null 2>&1; then
  run_logged pnpm_store pnpm store prune
fi
if command -v pip3 >/dev/null 2>&1; then
  run_logged pip_cache pip3 cache purge
elif command -v pip >/dev/null 2>&1; then
  run_logged pip_cache pip cache purge
fi
if command -v conda >/dev/null 2>&1; then
  run_logged conda_clean conda clean --all --yes
fi

# Allowlisted leaf caches only — never ~/.cache or ~/Library/Caches wholesale.
purge_allowlisted_leaf() {
  local label="$1"
  local path="$2"
  case "$path" in
    "$HOME/.cache/uv"|"$HOME/Library/Caches/Google") ;;
    *) die "not an allowlisted cache leaf: $path" ;;
  esac
  require_safe_user_delete_path "$path"
  if [ -e "$path" ]; then
    run_logged "$label" rm -rf "$path"
  else
    printf 'SKIP %s (absent)\n' "$label" >> "$LOG_FILE"
  fi
}

if command -v uv >/dev/null 2>&1; then
  run_logged uv_cache uv cache clean --force
elif [ -e "$HOME/.cache/uv" ]; then
  purge_allowlisted_leaf uv_cache "$HOME/.cache/uv"
else
  printf 'SKIP uv_cache (absent)\n' >> "$LOG_FILE"
fi

purge_allowlisted_leaf chrome_cache "$HOME/Library/Caches/Google"

if is_true "${XCODE_DERIVED_PURGE:-false}"; then
  DERIVED="$HOME/Library/Developer/Xcode/DerivedData"
  if [ -d "$DERIVED" ]; then
    require_safe_user_delete_path "$DERIVED"
    run_logged xcode_derived rm -rf "$DERIVED"
  fi
else
  printf 'SKIP xcode_derived (XCODE_DERIVED_PURGE is not true)\n' >> "$LOG_FILE"
fi

AFTER_FREE="$(free_kib_for_path "$DATA_VOLUME")"
printf 'free_kib_before=%s\nfree_kib_after=%s\n' "$BEFORE_FREE" "$AFTER_FREE" >> "$LOG_FILE"
FINISHED_AT="$(now_iso)"
write_action_receipt purge_stale_caches "$STATUS" "$STARTED_AT" "$FINISHED_AT" "$LOG_FILE" >/dev/null
[ "$STATUS" = success ] || exit 1
