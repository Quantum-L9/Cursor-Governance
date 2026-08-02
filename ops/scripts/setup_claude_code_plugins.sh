#!/usr/bin/env bash
# Declarative, idempotent Claude Code (the `claude` CLI) plugin setup.
#
# Portability note: Claude Code plugin state lives in $HOME/.claude/ (user scope),
# which sits outside any git repo and is NOT portable — ~/.claude.json also carries
# a live OAuth session (oauthAccount, machineID, userID) that must never be checked
# into git. ~/.claude/plugins/ is a local cache of full marketplace clones (100s of
# MB) and is likewise not something to vendor here. What IS portable and safe to
# version-control is the small *declaration* of desired state below.
#
# Enablement is now per-class, not uniformly user-scoped (environment/plugins/,
# see rules/84-cursor-governance-wiring.mdc v3.0.0 + README.md in that dir). Only
# the marketplace clone cache under ~/.claude/plugins/ stays purely local/user-scope
# for every repo — CORE_PLUGINS below install at `-s user` (every governed repo gets
# them), while CLASS_PLUGINS install at `-s project`, writing to
# <workspace>/.claude/settings.json, and only for the workspace class each entry
# is gated to (per environment/plugins/exceptions.yaml classification).
#
# Activation: Cursor-Governance sessionStart + setup_workspace_symlinks.sh call this
# in --quiet mode whenever a workspace is wired, passing --workspace explicitly so
# project-scope installs land in the right repo (sessionStart's cwd is the hooks
# dir, not the open workspace — see session_start_bootstrap.sh's CURSOR_PROJECT_DIR).
#
# Usage:
#   bash ops/scripts/setup_claude_code_plugins.sh                        # cwd = workspace
#   bash ops/scripts/setup_claude_code_plugins.sh --workspace /path/repo # explicit workspace
#   bash ops/scripts/setup_claude_code_plugins.sh --quiet                # hook-safe: no update, fail-open
#   bash ops/scripts/setup_claude_code_plugins.sh --update               # force claude update first
#
# Requires: `claude` (Claude Code CLI) already installed and reachable on PATH.
# Install docs: https://docs.claude.com/en/docs/claude-code
# Note: marketplace schemas advance with the CLI — keep Claude Code current.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLASSIFIER="$SCRIPT_DIR/../hooks/workspace_open_plugin_loader.py"

QUIET=0
FORCE_UPDATE=0
WORKSPACE_DIR="$(pwd)"
while [ $# -gt 0 ]; do
  case "$1" in
    --quiet|-q) QUIET=1; shift ;;
    --update) FORCE_UPDATE=1; shift ;;
    --workspace)
      WORKSPACE_DIR="$2"
      shift 2
      ;;
    -h|--help)
      sed -n '2,32p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      shift
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

# --- Classification: which capabilities does this workspace get? -----------
# Single source of truth for odoo_plasticos/aws_infra/zep_memory/core_default
# lives in workspace_open_plugin_loader.py (shared with the Cursor workspaceOpen
# hook) — not re-implemented here. Fails open to core_default on any error.
classify_workspace_class() {
  local ws="$1"
  if [ -f "$CLASSIFIER" ] && command -v python3 >/dev/null 2>&1; then
    python3 "$CLASSIFIER" --classify "$ws" 2>/dev/null || echo "core_default"
  else
    echo "core_default"
  fi
}

WORKSPACE_CLASS="$(classify_workspace_class "$WORKSPACE_DIR")"

# --- Desired state (edit here to add/remove plugins) -----------------------
# Parallel arrays (not associative — macOS ships bash 3.2, no `declare -A` support):

# Always installed at `-s user` — every governed workspace, regardless of class.
CORE_MARKETPLACE_REPOS=(
  "anthropics/claude-plugins-official"
)
CORE_PLUGINS=(
  "hookify@claude-plugins-official"
  "pr-review-toolkit@claude-plugins-official"
  "desktop-commander@claude-plugins-official"
  "context7@claude-plugins-official"
)

# Class-gated: installed at `-s project` (writes <workspace>/.claude/settings.json),
# only when WORKSPACE_CLASS matches. Parallel arrays, index-aligned.
CLASS_NAMES=("aws_infra" "zep_memory")
CLASS_MARKETPLACE_REPOS=("anthropics/claude-plugins-official" "getzep/zep")
CLASS_PLUGIN_ENTRIES=("aws-core@claude-plugins-official" "building-with-zep@zep")
# odoo_plasticos has no Claude-side addon modeled (environment/plugins/README.md)
# -- intentionally absent from CLASS_NAMES, not a placeholder gap.

# One-time migration: before Phase 7, CLASS_PLUGIN_ENTRIES above were installed
# unconditionally at `-s user` for every workspace (the exact problem this rewrite
# fixes -- a pure-Python repo with zero AWS/Zep surface still got aws-core and
# building-with-zep). Scoping new installs to `-s project` does not retroactively
# remove a pre-existing `-s user` install, so it must be uninstalled explicitly or
# every workspace keeps it forever regardless of class. Always retire these from
# user scope, unconditionally -- the correct location going forward is `-s project`,
# installed per-workspace-class below, never `-s user`.
RETIRED_USER_SCOPE_PLUGINS=(
  "aws-core@claude-plugins-official"
  "building-with-zep@zep"
)
# -----------------------------------------------------------------------------

# marketplace short name (last path segment) for `marketplace update`
marketplace_name() {
  echo "${1##*/}"
}

plugin_name() {
  # building-with-zep@zep → building-with-zep
  echo "${1%%@*}"
}

# Resolve the marketplaces + plugins actually desired for WORKSPACE_CLASS.
MARKETPLACE_REPOS=("${CORE_MARKETPLACE_REPOS[@]}")
CLASS_PLUGINS=()
for i in "${!CLASS_NAMES[@]}"; do
  if [ "${CLASS_NAMES[$i]}" = "$WORKSPACE_CLASS" ]; then
    CLASS_PLUGINS+=("${CLASS_PLUGIN_ENTRIES[$i]}")
    mp="${CLASS_MARKETPLACE_REPOS[$i]}"
    known=0
    for existing in "${MARKETPLACE_REPOS[@]}"; do
      [ "$existing" = "$mp" ] && known=1
    done
    [ "$known" -eq 0 ] && MARKETPLACE_REPOS+=("$mp")
  fi
done
# bash 3.2 (macOS default) treats "${empty_array[@]}" as unbound under `set -u`,
# so CLASS_PLUGINS (often empty, e.g. core_default) is appended conditionally.
PLUGINS=("${CORE_PLUGINS[@]}")
if [ "${#CLASS_PLUGINS[@]}" -gt 0 ]; then
  PLUGINS+=("${CLASS_PLUGINS[@]}")
fi

STAMP_DIR="$HOME/.claude/plugins"
# Per-class stamp: switching between two differently-classed workspaces on the
# same machine must re-check (different desired state), but repeated runs on
# the *same* workspace class stay a no-op — this is what Phase 7 requires.
STAMP_FILE="$STAMP_DIR/.l9-plugin-desired-hash-${WORKSPACE_CLASS}"
DESIRED_HASH="$(printf '%s\n' "${MARKETPLACE_REPOS[@]}" "${PLUGINS[@]}" | shasum -a 256 | awk '{print $1}')"

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
log "Workspace: $WORKSPACE_DIR (class: $WORKSPACE_CLASS)"


# Reconcile the governance skill corpus into Claude Code's native discovery
# locations. This happens before the plugin stamp fast path because skill state
# changes independently of marketplace plugin state.
GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -f "$SCRIPT_DIR/reconcile_claude_l9_skills.py" ]; then
  python3 "$SCRIPT_DIR/reconcile_claude_l9_skills.py" \
    --root "$GOV_ROOT" --scope user --scope project \
    --workspace "$WORKSPACE_DIR" --quiet \
    || echo "WARN: L9 Claude skill reconciliation reported drift or a local name conflict" >&2
fi

# Migration cleanup runs unconditionally, ahead of the per-class stamp fast path
# below, so a stamped/already-correct workspace can't mask a stale user-scope
# install left over from before Phase 7 forever.
for plugin in "${RETIRED_USER_SCOPE_PLUGINS[@]}"; do
  name="$(plugin_name "$plugin")"
  if list_installed | grep -Fqi "$name"; then
    log "Migration cleanup: removing stale user-scope install: $plugin"
    claude plugin uninstall -s user -y "$name" 2>/dev/null \
      || echo "WARN: migration cleanup uninstall failed (may not be at user scope): $plugin" >&2
  fi
done

# Fast path: desired set already present and stamp matches → nothing to do.
mkdir -p "$STAMP_DIR"
if [ -f "$STAMP_FILE" ] && [ "$(cat "$STAMP_FILE" 2>/dev/null || true)" = "$DESIRED_HASH" ] && all_desired_installed; then
  log "OK: Claude Code plugins already match Cursor-Governance desired state (class: $WORKSPACE_CLASS)"
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
for plugin in "${CORE_PLUGINS[@]}"; do
  log "Plugin (user scope): $plugin"
  if ! claude plugin install -s user "$plugin"; then
    echo "WARN: plugin install failed: $plugin" >&2
  fi
done

if [ "${#CLASS_PLUGINS[@]}" -gt 0 ]; then
  log ""
  log "Class-gated plugins for '$WORKSPACE_CLASS' (project scope -> $WORKSPACE_DIR/.claude/settings.json):"
  for plugin in "${CLASS_PLUGINS[@]}"; do
    log "Plugin (project scope): $plugin"
    if ! (cd "$WORKSPACE_DIR" && claude plugin install -s project "$plugin"); then
      echo "WARN: plugin install failed: $plugin" >&2
    fi
  done
fi

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
