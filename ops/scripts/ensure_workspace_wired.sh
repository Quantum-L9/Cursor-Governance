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
#
# Plans-store mode (L9_PLANS_STORE_MODE):
#   migrate    (default) manual setup callers — ensure_machine_cursor_plans_store
#              may migrate a legacy real ~/.cursor/plans directory into the
#              tracked store (copy, rename aside, replace with a symlink).
#   links-only SessionStart — the store helper runs only when ~/.cursor/plans
#              does not exist at all (nothing to read, migrate, archive, or
#              rewrite). Any existing entry is left byte-for-byte untouched
#              and the workspace .cursor/plans link points at it as-is; a
#              dangling entry is a WARN naming the manual setup, never a
#              migration (SESSIONSTART_NO_PLAN_SURFACE_V1).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"
# shellcheck source=lib/workspace_kind.sh
source "$SCRIPT_DIR/lib/workspace_kind.sh"
# shellcheck source=lib/workspace_link_health.sh
source "$SCRIPT_DIR/lib/workspace_link_health.sh"
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

PLANS_STORE_MODE="${L9_PLANS_STORE_MODE:-migrate}"
case "$PLANS_STORE_MODE" in
  migrate|links-only) ;;
  *)
    echo "ERROR: L9_PLANS_STORE_MODE must be 'migrate' or 'links-only' (got: $PLANS_STORE_MODE)" >&2
    exit 2
    ;;
esac
HOME_PLANS="$HOME/.cursor/plans"

# links-only: invoke the store helper only for an absent ~/.cursor/plans (its
# sole action is then to create the link — the P564-F1 repair). An existing
# entry — real directory, real file, healthy or dangling symlink — is never
# handed to the helper, so it cannot be copied, renamed aside, re-pointed or
# replaced from a SessionStart.
_plans_store_prepare() {
  if [ "$PLANS_STORE_MODE" = "migrate" ]; then
    ensure_machine_cursor_plans_store
    return 0
  fi
  if [ ! -e "$HOME_PLANS" ] && [ ! -L "$HOME_PLANS" ]; then
    ensure_machine_cursor_plans_store
    return 0
  fi
  if [ -L "$HOME_PLANS" ] && [ ! -e "$HOME_PLANS" ]; then
    echo "WARN: ~/.cursor/plans is a dangling symlink — left untouched (L9_PLANS_STORE_MODE=links-only); run setup_workspace_symlinks.sh or /wire to repair the machine plans store"
    return 0
  fi
  if [ ! -L "$HOME_PLANS" ]; then
    echo "WARN: ~/.cursor/plans is a real directory — not migrated (L9_PLANS_STORE_MODE=links-only); run setup_workspace_symlinks.sh or /wire to migrate it into the tracked store"
    return 0
  fi
  echo "OK: ~/.cursor/plans left as-is (L9_PLANS_STORE_MODE=links-only)"
}

# The workspace link is written whenever ~/.cursor/plans resolves; a dangling
# store entry gets no link (it could only dangle too) and the caller's health
# predicate reports the workspace unhealthy rather than this script migrating.
_plans_link() {
  if [ "$PLANS_STORE_MODE" = "links-only" ] && [ ! -e "$HOME_PLANS" ]; then
    echo "WARN: .cursor/plans link not written — ~/.cursor/plans does not resolve (L9_PLANS_STORE_MODE=links-only)"
    return 0
  fi
  _link_or_update "$WORKSPACE/.cursor/plans" "$HOME_PLANS" ".cursor/plans"
}

_link_ok() {
  workspace_link_realpath_ok "$1" "$2"
}

_link_or_update() {
  local link=$1 target=$2 label=$3
  mkdir -p "$(dirname "$link")"
  if [ -L "$link" ]; then
    # Same predicate as the health check: right realpath AND reachable
    # terminal target. A dangling link is re-created, never reported OK.
    if _link_ok "$link" "$target"; then
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
if workspace_links_healthy "$WORKSPACE" \
  && _link_ok "$WORKSPACE/.cursor/governance/CANONICAL_LAW.md" "$GOV_ROOT/CANONICAL_LAW.md"; then
  already_wired=1
fi

if [ "$already_wired" -eq 1 ]; then
  echo "OK: workspace already wired: $WORKSPACE"
  exit 0
fi

echo "WIRE: $WORKSPACE (consumer .cursor links)"
WORKSPACE_DIR="$WORKSPACE"
_plans_store_prepare
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
_plans_link
_link_or_update "$HOME/.cursor/plugins/local/l9-governance" "$GC" \
  "~/.cursor/plugins/local/l9-governance"

if [ "${L9_WIRE_LINKS_ONLY:-0}" = "1" ]; then
  echo "OK: links-only wire (L9_WIRE_LINKS_ONLY=1)"
  exit 0
fi

echo "WIRE: $WORKSPACE (setup_workspace_symlinks.sh)"
(
  cd "$WORKSPACE"
  bash "$SCRIPT_DIR/setup_workspace_symlinks.sh"
)
