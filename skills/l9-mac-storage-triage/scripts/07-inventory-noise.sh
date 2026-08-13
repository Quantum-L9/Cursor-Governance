#!/bin/bash
# l9-mac-storage-triage / scripts/07-inventory-noise.sh
# purpose: bounded read-only sizes for allowlisted caches, docker reclaimable, trash
# skill_schema: 1 parent: l9-mac-storage-triage layer: script role: inventory
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
require_macos
require_diagnosis

REPORT_DIR="$(latest_report_dir_from_state)"
TIMEOUT_SECONDS="${COMMAND_TIMEOUT_SECONDS:-25}"
INV="$REPORT_DIR/noise-inventory.env"
MD="$REPORT_DIR/noise-inventory.md"

# Hard timeout via perl alarm so du/docker cannot ignore SIGTERM.
run_limited() {
  local seconds="$1"
  shift
  perl -e 'alarm shift; exec @ARGV' "$seconds" "$@"
}

kib_of() {
  local path="$1"
  if [ -e "$path" ]; then
    log "sizing $path" >&2
    run_limited "$TIMEOUT_SECONDS" du -sk "$path" 2>/dev/null | awk '{print $1}'
  fi
}

kib_or_zero() {
  local value
  value="$(kib_of "$1" || true)"
  value="$(printf '%s\n' "$value" | awk 'NF{print $1; exit}')"
  if [ -n "${value:-}" ] && [ "$value" -ge 0 ] 2>/dev/null; then
    printf '%s\n' "$value"
  else
    printf '0\n'
  fi
}

log "Collecting bounded noise inventory (read-only)"

BREW_CACHE_PATH='MISSING'
BREW_CACHE_KIB=0
if command -v brew >/dev/null 2>&1; then
  BREW_CACHE_PATH="$(brew --cache 2>/dev/null || printf 'MISSING')"
  if [ -n "$BREW_CACHE_PATH" ] && [ "$BREW_CACHE_PATH" != "MISSING" ]; then
    BREW_CACHE_KIB="$(kib_or_zero "$BREW_CACHE_PATH")"
  fi
fi

NPM_CACHE_KIB=0
YARN_CACHE_KIB=0
PNPM_CACHE_KIB=0
PIP_CACHE_KIB=0
CONDA_PKGS_KIB=0
if [ -d "$HOME/.npm" ]; then NPM_CACHE_KIB="$(kib_or_zero "$HOME/.npm")"; fi
if [ -d "$HOME/Library/Caches/Yarn" ]; then YARN_CACHE_KIB="$(kib_or_zero "$HOME/Library/Caches/Yarn")"; fi
if [ -d "$HOME/Library/pnpm" ]; then PNPM_CACHE_KIB="$(kib_or_zero "$HOME/Library/pnpm")"; fi
if [ -d "$HOME/Library/Caches/pip" ]; then PIP_CACHE_KIB="$(kib_or_zero "$HOME/Library/Caches/pip")"; fi
if [ -d "$HOME/.cache/pip" ]; then
  extra="$(kib_or_zero "$HOME/.cache/pip")"
  PIP_CACHE_KIB=$((PIP_CACHE_KIB + extra))
fi
if [ -d "$HOME/miniconda3/pkgs" ]; then CONDA_PKGS_KIB="$(kib_or_zero "$HOME/miniconda3/pkgs")"; fi
if [ -d "$HOME/anaconda3/pkgs" ]; then
  extra="$(kib_or_zero "$HOME/anaconda3/pkgs")"
  CONDA_PKGS_KIB=$((CONDA_PKGS_KIB + extra))
fi
UV_CACHE_KIB=0
GOOGLE_CACHE_KIB=0
if [ -d "$HOME/.cache/uv" ]; then UV_CACHE_KIB="$(kib_or_zero "$HOME/.cache/uv")"; fi
if [ -d "$HOME/Library/Caches/Google" ]; then GOOGLE_CACHE_KIB="$(kib_or_zero "$HOME/Library/Caches/Google")"; fi

XCODE_DERIVED_KIB=0
XCODE_DERIVED_PATH="$HOME/Library/Developer/Xcode/DerivedData"
if [ -d "$XCODE_DERIVED_PATH" ]; then
  XCODE_DERIVED_KIB="$(kib_or_zero "$XCODE_DERIVED_PATH")"
fi

TRASH_KIB="$(kib_or_zero "$HOME/.Trash")"

DOCKER_AVAILABLE='false'
DOCKER_RECLAIMABLE_NOTE='unavailable'
DOCKER_STOPPED_CONTAINERS=0
DOCKER_DANGLING_IMAGES=0
if command -v docker >/dev/null 2>&1; then
  if run_limited 8 docker info >/dev/null 2>&1; then
    DOCKER_AVAILABLE='true'
    run_limited 12 docker system df > "$REPORT_DIR/docker-system-df.txt" 2>&1 || true
    DOCKER_STOPPED_CONTAINERS="$(run_limited 8 docker ps -aq --filter status=exited 2>/dev/null | wc -l | tr -d ' ' || printf '0')"
    DOCKER_DANGLING_IMAGES="$(run_limited 8 docker images -q --filter dangling=true 2>/dev/null | wc -l | tr -d ' ' || printf '0')"
    DOCKER_RECLAIMABLE_NOTE="stopped_containers=${DOCKER_STOPPED_CONTAINERS} dangling_images=${DOCKER_DANGLING_IMAGES}"
  else
    DOCKER_RECLAIMABLE_NOTE='daemon_not_running'
  fi
fi

CACHE_TOTAL_KIB=$((BREW_CACHE_KIB + NPM_CACHE_KIB + YARN_CACHE_KIB + PNPM_CACHE_KIB + PIP_CACHE_KIB + CONDA_PKGS_KIB + UV_CACHE_KIB + GOOGLE_CACHE_KIB))
gib() { awk -v k="$1" 'BEGIN {printf "%.2f", k/1048576}'; }

{
  printf "BREW_CACHE_PATH='%s'\n" "$BREW_CACHE_PATH"
  printf "BREW_CACHE_KIB='%s'\n" "$BREW_CACHE_KIB"
  printf "NPM_CACHE_KIB='%s'\n" "$NPM_CACHE_KIB"
  printf "YARN_CACHE_KIB='%s'\n" "$YARN_CACHE_KIB"
  printf "PNPM_CACHE_KIB='%s'\n" "$PNPM_CACHE_KIB"
  printf "PIP_CACHE_KIB='%s'\n" "$PIP_CACHE_KIB"
  printf "CONDA_PKGS_KIB='%s'\n" "$CONDA_PKGS_KIB"
  printf "UV_CACHE_KIB='%s'\n" "$UV_CACHE_KIB"
  printf "GOOGLE_CACHE_KIB='%s'\n" "$GOOGLE_CACHE_KIB"
  printf "CACHE_TOTAL_KIB='%s'\n" "$CACHE_TOTAL_KIB"
  printf "XCODE_DERIVED_KIB='%s'\n" "$XCODE_DERIVED_KIB"
  printf "TRASH_KIB='%s'\n" "$TRASH_KIB"
  printf "DOCKER_AVAILABLE='%s'\n" "$DOCKER_AVAILABLE"
  printf "DOCKER_STOPPED_CONTAINERS='%s'\n" "$DOCKER_STOPPED_CONTAINERS"
  printf "DOCKER_DANGLING_IMAGES='%s'\n" "$DOCKER_DANGLING_IMAGES"
  printf "DOCKER_RECLAIMABLE_NOTE='%s'\n" "$DOCKER_RECLAIMABLE_NOTE"
} > "$INV"

{
  printf '# Noise inventory (read-only)\n\n'
  printf -- '- Cache total: %s GiB (%s KiB)\n' "$(gib "$CACHE_TOTAL_KIB")" "$CACHE_TOTAL_KIB"
  printf -- '- Homebrew cache: %s GiB\n' "$(gib "$BREW_CACHE_KIB")"
  printf -- '- npm/yarn/pnpm: %s / %s / %s KiB\n' "$NPM_CACHE_KIB" "$YARN_CACHE_KIB" "$PNPM_CACHE_KIB"
  printf -- '- pip cache: %s KiB\n' "$PIP_CACHE_KIB"
  printf -- '- conda pkgs cache: %s KiB\n' "$CONDA_PKGS_KIB"
  printf -- '- uv cache: %s KiB\n' "$UV_CACHE_KIB"
  printf -- '- Chrome cache (Library/Caches/Google only): %s KiB\n' "$GOOGLE_CACHE_KIB"
  printf -- '- Xcode DerivedData: %s GiB (not auto-purged unless XCODE_DERIVED_PURGE=true)\n' "$(gib "$XCODE_DERIVED_KIB")"
  printf -- '- Docker: %s (%s)\n' "$DOCKER_AVAILABLE" "$DOCKER_RECLAIMABLE_NOTE"
  if [ -f "$REPORT_DIR/docker-system-df.txt" ]; then
    printf -- '- Docker volumes (not allowlisted, not pruned): see docker-system-df.txt\n'
  fi
  printf -- '- Trash: %s GiB (0 with Full Disk Access denied still means Unknown)\n\n' "$(gib "$TRASH_KIB")"
  printf 'macOS `~/Library/Containers` was not inventoried for deletion.\n'
} > "$MD"

printf '%s\n' "$INV" > "$(state_dir)/noise-inventory-path"
log "Noise inventory written: $MD"
