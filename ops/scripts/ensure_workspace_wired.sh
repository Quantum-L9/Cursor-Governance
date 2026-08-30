#!/usr/bin/env bash
# Idempotent: wire gitignored .cursor* links in a workspace folder.
# Not sessionStart. Used after git worktree add / clone, and as make pr heal.
#
# Always writes the three consumer links (or SSOT-safe variant). Full
# setup_workspace_symlinks.sh (hooks, IDE, plugins) runs unless
# L9_WIRE_LINKS_ONLY=1 — Python isolate/lane creators set that so they
# do not pay a 30–90s machine reconcile on every worktree.
#
# Kind split matches setup_workspace_symlinks.sh C10: ssot and
# ssot_checkout never get .cursor-commands. Links-only must honor that
# too — make pr heals via this script and exits before setup.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"
# shellcheck source=lib/workspace_kind.sh
source "$SCRIPT_DIR/lib/workspace_kind.sh"
# shellcheck source=lib/cursor_plans_store.sh
source "$SCRIPT_DIR/lib/cursor_plans_store.sh"

WORKSPACE="${1:-$(pwd)}"
if [ ! -d "$WORKSPACE" ]; then
  echo "ERROR: workspace not a directory: $WORKSPACE" >&2
  exit 1
fi

if ! resolve_governance_paths; then
  echo "WARN: skip wire — governance SSOT not at \$HOME/.cursor-governance"
  exit 0
fi

GC="$GLOBAL_COMMANDS"
WS_KIND="$(classify_workspace_kind "$WORKSPACE")"

_link_ok() {
  local link=$1 expected=$2
  [ -L "$link" ] || return 1
  local rt re
  rt="$(python3 -c "import os; print(os.path.realpath('$link'))")"
  re="$(python3 -c "import os; print(os.path.realpath('$expected'))")"
  [ "$rt" = "$re" ]
}

_link_or_update() {
  local link=$1 target=$2 label=$3
  mkdir -p "$(dirname "$link")"
  if [ -L "$link" ]; then
    if [ "$(python3 -c "import os; print(os.path.realpath('$link'))")" = "$(python3 -c "import os; print(os.path.realpath('$target'))")" ]; then
      echo "OK: $label"
      return
    fi
    rm "$link"
  elif [ -e "$link" ]; then
    mv "$link" "${link}.backup.$(date +%Y%m%d_%H%M%S)"
  fi
  ln -sfn "$target" "$link"
  echo "LINKED: $label -> $target"
}

already_wired=0
if [ "$WS_KIND" = "ssot" ] || [ "$WS_KIND" = "ssot_checkout" ]; then
  if [ ! -e "$WORKSPACE/.cursor-commands" ] && [ ! -L "$WORKSPACE/.cursor-commands" ] \
    && _link_ok "$WORKSPACE/.cursor/plans" "$HOME/.cursor/plans" \
    && _link_ok "$WORKSPACE/.cursor/governance/CANONICAL_LAW.md" "$GOV_ROOT/CANONICAL_LAW.md"; then
    already_wired=1
  fi
elif _link_ok "$WORKSPACE/.cursor-commands" "$GC" \
  && _link_ok "$WORKSPACE/.cursor/plans" "$HOME/.cursor/plans" \
  && _link_ok "$WORKSPACE/.cursor/governance/CANONICAL_LAW.md" "$GOV_ROOT/CANONICAL_LAW.md"; then
  already_wired=1
fi

if [ "$already_wired" -eq 1 ]; then
  echo "OK: workspace already wired: $WORKSPACE"
  exit 0
fi

echo "WIRE: $WORKSPACE (consumer .cursor links)"
WORKSPACE_DIR="$WORKSPACE"
ensure_machine_cursor_plans_store
if [ "$WS_KIND" = "ssot" ] || [ "$WS_KIND" = "ssot_checkout" ]; then
  if [ -e "$WORKSPACE/.cursor-commands" ] || [ -L "$WORKSPACE/.cursor-commands" ]; then
    rm -f "$WORKSPACE/.cursor-commands"
    if [ "$WS_KIND" = "ssot" ]; then
      echo "REMOVED: .cursor-commands self-alias"
    else
      echo "REMOVED: .cursor-commands on ssot_checkout (consumer link not required)"
    fi
  else
    echo "OK: .cursor-commands absent on $WS_KIND (no consumer link)"
  fi
else
  _link_or_update "$WORKSPACE/.cursor-commands" "$GC" ".cursor-commands"
fi
mkdir -p "$WORKSPACE/.cursor/governance"
_link_or_update "$WORKSPACE/.cursor/governance/CANONICAL_LAW.md" \
  "$GOV_ROOT/CANONICAL_LAW.md" ".cursor/governance/CANONICAL_LAW.md"
_link_or_update "$WORKSPACE/.cursor/plans" "$HOME/.cursor/plans" ".cursor/plans"

if [ "${L9_WIRE_LINKS_ONLY:-0}" = "1" ]; then
  echo "OK: links-only wire (L9_WIRE_LINKS_ONLY=1)"
  exit 0
fi

echo "WIRE: $WORKSPACE (setup_workspace_symlinks.sh)"
(
  cd "$WORKSPACE"
  bash "$SCRIPT_DIR/setup_workspace_symlinks.sh"
)
