#!/usr/bin/env bash
# IDE profile dispatcher — classify a workspace, then run every applicable adapter.
#
# This script owns exactly two things:
#   1. CLASSIFICATION — which workspace class this repo belongs to
#      (rules in environment/ide/exceptions.yaml).
#   2. DISPATCH — which adapters to run.
#
# Everything editor-specific lives in an adapter under ops/scripts/adapters/:
#   cursor.sh     extensions (machine scope) + .vscode/settings.json (repo scope).
#                 Runs whenever the profile is reconciled; the `cursor` CLI is
#                 optional, settings still merge without it.
#   agentdocs.sh  the generated formatter-ownership block in AGENTS.md / CLAUDE.md.
#                 Runs only where those files already exist. This is the branch that
#                 reaches cloud agents: .vscode/ is untracked, AGENTS.md is not.
#
# Language ownership is declared once, IDE-neutrally, in environment/ide/policy.json.
# Each adapter renders that policy for its own target. To change which formatter owns
# a language, edit policy.json — not an adapter, not a settings payload.
#
# Adapters for other editors (Zed, JetBrains) are deliberately absent: add one the
# first time a governed repo is actually opened in that editor, not speculatively.
#
# Workspace classes:
#   biome_default  — Biome owns JS/TS/JSON, Ruff owns Python
#   eslint_owned   — no JS/TS formatter declared; the repo's ESLint/Prettier config
#                    stays authoritative (formatter exclusivity)
#
# Usage:
#   bash ops/scripts/install_ide_profile.sh [WORKSPACE]           # default: $PWD
#   bash ops/scripts/install_ide_profile.sh --quiet [WORKSPACE]   # hook-safe, fail-open
#   bash ops/scripts/install_ide_profile.sh --force [WORKSPACE]   # ignore stamps
#   bash ops/scripts/install_ide_profile.sh --dry-run [WORKSPACE] # print, write nothing
#
# Requires: python3. `cursor` CLI optional.

set -euo pipefail

QUIET=0
FORCE=0
DRY_RUN=0
WORKSPACE=""

for arg in "$@"; do
  case "$arg" in
    --quiet|-q) QUIET=1 ;;
    --force) FORCE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      sed -n '2,38p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    -*) echo "WARN: unknown flag: $arg" >&2 ;;
    *) WORKSPACE="$arg" ;;
  esac
done

log() { [ "$QUIET" -eq 0 ] && echo "$@"; return 0; }

fail_open() {
  # sessionStart must never break a session over IDE cosmetics.
  if [ "$QUIET" -eq 1 ]; then
    echo "ide-profile: skipped ($1)"
    exit 0
  fi
  echo "ERROR: $1" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
. "$SCRIPT_DIR/resolve_governance_paths.sh"
resolve_governance_paths || fail_open "governance root not found at \$HOME/.cursor-governance"

IDE_DIR="${L9_IDE_DIR:-$GLOBAL_COMMANDS/environment/ide}"
[ -d "$IDE_DIR" ] || fail_open "IDE profile SSOT missing: $IDE_DIR"

ADAPTER_DIR="${L9_IDE_ADAPTER_DIR:-$SCRIPT_DIR/adapters}"
[ -d "$ADAPTER_DIR" ] || fail_open "adapter directory missing: $ADAPTER_DIR"

command -v python3 >/dev/null 2>&1 || fail_open "python3 not found on PATH"

WORKSPACE="${WORKSPACE:-$PWD}"
[ -d "$WORKSPACE" ] || fail_open "workspace not a directory: $WORKSPACE"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"

# This script writes .vscode/settings.json and the AGENTS.md formatter block.
# Doing that while `make pr` runs puts the write inside a pre-commit hook's
# window, which pre-commit then reports as "files were modified by this hook"
# against a hook that never wrote. Wait for the repo-write lock; a --quiet
# (hook-driven) run yields entirely, an explicit run proceeds with a warning.
LOCK_LIB="$SCRIPT_DIR/lib/repo_write_lock.sh"
if [ "$DRY_RUN" -eq 0 ] && [ -f "$LOCK_LIB" ]; then
  # shellcheck source=lib/repo_write_lock.sh
  . "$LOCK_LIB"
  export L9_REPO_WRITE_LOCK_LABEL="install_ide_profile"
  if ! repo_write_lock_acquire "$WORKSPACE" "${L9_IDE_LOCK_WAIT_S:-45}"; then
    if [ "$QUIET" -eq 1 ]; then
      echo "ide-profile: skipped ($(repo_write_lock_skip_note "$WORKSPACE"))"
      exit 0
    fi
    echo "WARN: $(repo_write_lock_skip_note "$WORKSPACE") — reconciling anyway (explicit run)" >&2
  else
    trap 'repo_write_lock_release' EXIT
  fi
fi

# --- Classification -----------------------------------------------------------
# 1) basename match  2) any path-segment match  3) eslint markers without biome markers

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

ESLINT_REPOS="$(
  awk '
    /^eslint_owned_repos:/ { grab = 1; next }
    grab && /^[[:space:]]*-[[:space:]]*/ { sub(/^[[:space:]]*-[[:space:]]*/, ""); print; next }
    grab && /^[^[:space:]#]/ { grab = 0 }
  ' "$IDE_DIR/exceptions.yaml" 2>/dev/null || true
)"

classify() {
  local ws="$1" repo seg base
  base="$(lower "$(basename "$ws")")"
  while IFS= read -r repo; do
    [ -n "$repo" ] || continue
    repo="$(lower "$repo")"
    [ "$base" = "$repo" ] && { echo eslint_owned; return; }
    # shellcheck disable=SC2001
    for seg in $(echo "$(lower "$ws")" | tr '/' ' '); do
      [ "$seg" = "$repo" ] && { echo eslint_owned; return; }
    done
  done <<EOF
$ESLINT_REPOS
EOF

  local has_eslint=0 has_biome=0
  if find "$ws" -maxdepth 2 \( -name 'eslint.config.*' -o -name '.eslintrc*' \) \
       -not -path '*/node_modules/*' -print -quit 2>/dev/null | grep -q .; then
    has_eslint=1
  fi
  if find "$ws" -maxdepth 2 \( -name 'biome.json' -o -name 'biome.jsonc' \) \
       -not -path '*/node_modules/*' -print -quit 2>/dev/null | grep -q .; then
    has_biome=1
  fi
  if [ "$has_eslint" -eq 1 ] && [ "$has_biome" -eq 0 ]; then
    echo eslint_owned
  else
    echo biome_default
  fi
}

WS_CLASS="$(classify "$WORKSPACE")"
log "Workspace: $WORKSPACE"
log "Class:     $WS_CLASS"

# --- Dispatch -----------------------------------------------------------------

ADAPTER_FLAGS=()
[ "$DRY_RUN" -eq 1 ] && ADAPTER_FLAGS+=(--dry-run)
[ "$FORCE" -eq 1 ] && ADAPTER_FLAGS+=(--force)
[ "$QUIET" -eq 1 ] && ADAPTER_FLAGS+=(--quiet)

SUMMARY=""

run_adapter() {
  # Every adapter prints its result as space-separated key=value pairs on stdout, so
  # the summary is just concatenation. An adapter failure degrades the summary but
  # never aborts the others: a broken agent-docs render must not cost you your
  # editor settings.
  local name="$1" script="$ADAPTER_DIR/$1.sh" out=""
  if [ ! -f "$script" ]; then
    SUMMARY="$SUMMARY $name=missing"
    return 0
  fi
  if out="$(bash "$script" "$WORKSPACE" "$WS_CLASS" ${ADAPTER_FLAGS+"${ADAPTER_FLAGS[@]}"})"; then
    SUMMARY="$SUMMARY $out"
  else
    echo "WARN: adapter '$name' failed" >&2
    SUMMARY="$SUMMARY $name=failed"
  fi
}

run_adapter cursor
run_adapter agentdocs

log "Adapters: $SUMMARY"
[ "$QUIET" -eq 1 ] && echo "ide-profile: $WS_CLASS$SUMMARY"
exit 0
