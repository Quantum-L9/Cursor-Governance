#!/usr/bin/env bash
# Declarative, idempotent Claude Code (the `claude` CLI) plugin setup.
#
# Portability note: Claude Code plugin state lives in $HOME/.claude/ (user scope),
# which sits outside any git repo and is NOT portable — ~/.claude.json also carries
# a live OAuth session (oauthAccount, machineID, userID) that must never be checked
# into git. ~/.claude/plugins/ is a local cache of full marketplace clones (100s of
# MB) and is likewise not something to vendor here. What IS portable and safe to
# version-control is the small *declaration* of desired state: which marketplaces
# and which plugins should be enabled. That declaration lives below, and this
# script reconciles any machine to match it by calling the `claude` CLI directly
# (both `marketplace add` and `plugin install` are no-ops if already satisfied).
#
# Activation: Cursor-Governance sessionStart + setup_workspace_symlinks.sh call this
# in --quiet mode whenever GlobalCommands is wired into a workspace, so the desired
# set stays installed for every governed repo (user-scope = machine-wide).
#
# Usage:
#   bash ops/scripts/setup_claude_code_plugins.sh           # full (may run claude update)
#   bash ops/scripts/setup_claude_code_plugins.sh --quiet    # hook-safe: no update, fail-open
#   bash ops/scripts/setup_claude_code_plugins.sh --update   # force claude update first
#
# Requires: `claude` (Claude Code CLI) already installed and reachable on PATH.
# Install docs: https://docs.claude.com/en/docs/claude-code
# Note: marketplace schemas advance with the CLI — keep Claude Code current.

set -euo pipefail

QUIET=0
FORCE_UPDATE=0
for arg in "$@"; do
  case "$arg" in
    --quiet|-q) QUIET=1 ;;
    --update) FORCE_UPDATE=1 ;;
    -h|--help)
      sed -n '2,24p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
  esac
done

log() {
  if [ "$QUIET" -eq 0 ]; then
    echo "$@"
  fi
}

# Prefer the native install (~/.local/bin) over a stale npm-global copy.
if [ -x "$HOME/.local/bin/claude" ]; then
  export PATH="$HOME/.local/bin:$PATH"
fi

# --- Desired state (edit here to add/remove plugins) -----------------------
# Parallel arrays (not associative — macOS ships bash 3.2, no `declare -A` support):
# "owner/repo" GitHub sources for `claude plugin marketplace add`
MARKETPLACE_REPOS=(
  "getzep/zep"
  "anthropics/claude-plugins-official"
)

# marketplace short name (last path segment) for `marketplace update`
marketplace_name() {
  echo "${1##*/}"
}

# "plugin@marketplace" entries for `claude plugin install`
PLUGINS=(
  "building-with-zep@zep"
  "aws-core@claude-plugins-official"
  "hookify@claude-plugins-official"
  "pr-review-toolkit@claude-plugins-official"
  "desktop-commander@claude-plugins-official"
  "context7@claude-plugins-official"
)
# -----------------------------------------------------------------------------

STAMP_DIR="$HOME/.claude/plugins"
STAMP_FILE="$STAMP_DIR/.l9-plugin-desired-hash"
DESIRED_HASH="$(printf '%s\n' "${MARKETPLACE_REPOS[@]}" "${PLUGINS[@]}" | shasum -a 256 | awk '{print $1}')"

plugin_name() {
  # building-with-zep@zep → building-with-zep
  echo "${1%%@*}"
}

list_installed() {
  claude plugin list 2>/dev/null || true
}

marketplace_known() {
  local name="$1"
  claude plugin marketplace list 2>/dev/null | grep -Fqi "$name"
}

all_desired_installed() {
  local installed name plugin
  installed="$(list_installed)"
  # "No plugins installed" or empty → not satisfied
  if [ -z "$installed" ] || echo "$installed" | grep -qi 'No plugins installed'; then
    return 1
  fi
  for plugin in "${PLUGINS[@]}"; do
    name="$(plugin_name "$plugin")"
    if ! echo "$installed" | grep -Fqi "$name"; then
      return 1
    fi
  done
  return 0
}

ensure_marketplace() {
  local repo="$1"
  local name
  name="$(marketplace_name "$repo")"
  if marketplace_known "$name"; then
    log "Marketplace update: $name"
    claude plugin marketplace update "$name" || {
      echo "WARN: marketplace update failed: $name" >&2
      return 0
    }
    return 0
  fi
  log "Marketplace add: $repo"
  if ! claude plugin marketplace add "$repo"; then
    echo "WARN: marketplace add failed: $repo" >&2
    return 0
  fi
}

if ! command -v claude >/dev/null 2>&1; then
  if [ "$QUIET" -eq 1 ]; then
    # sessionStart must not fail closed on missing Claude CLI
    exit 0
  fi
  echo "ERROR: 'claude' CLI not found on PATH." >&2
  echo "  Install: https://docs.claude.com/en/docs/claude-code" >&2
  echo "  (If installed via nvm-managed Node, add that Node's bin/ dir to PATH.)" >&2
  exit 1
fi

log "Claude Code CLI: $(command -v claude) ($(claude --version 2>/dev/null || echo unknown))"

# Fast path: desired set already present and stamp matches → nothing to do.
mkdir -p "$STAMP_DIR"
if [ -f "$STAMP_FILE" ] && [ "$(cat "$STAMP_FILE" 2>/dev/null || true)" = "$DESIRED_HASH" ] && all_desired_installed; then
  log "OK: Claude Code plugins already match Cursor-Governance desired state"
  [ "$QUIET" -eq 1 ] || claude plugin list
  exit 0
fi

# Self-heal: old Claude Code versions ship stale/retired default model IDs and
# reject newer marketplace schemas. Keep CLI current on interactive/--update runs.
# Skip on --quiet (sessionStart) unless --update; network update is too slow for hooks.
if [ "$QUIET" -eq 0 ] || [ "$FORCE_UPDATE" -eq 1 ]; then
  log "Checking for Claude Code updates..."
  claude update || echo "WARN: 'claude update' failed — continuing with current version" >&2
  log ""
fi

for repo in "${MARKETPLACE_REPOS[@]}"; do
  ensure_marketplace "$repo"
done

log ""
for plugin in "${PLUGINS[@]}"; do
  log "Plugin: $plugin"
  if ! claude plugin install -s user "$plugin"; then
    echo "WARN: plugin install failed: $plugin" >&2
  fi
done

if all_desired_installed; then
  printf '%s\n' "$DESIRED_HASH" > "$STAMP_FILE"
  log ""
  log "=== Installed plugins ==="
  [ "$QUIET" -eq 1 ] || claude plugin list
  exit 0
fi

if [ "$QUIET" -eq 1 ]; then
  # Fail-open for sessionStart — stamp absent so next session retries
  rm -f "$STAMP_FILE" 2>/dev/null || true
  exit 0
fi

echo "ERROR: Claude Code plugins still missing after reconcile." >&2
claude plugin list >&2 || true
exit 1
