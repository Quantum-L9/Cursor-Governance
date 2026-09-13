#!/usr/bin/env bash
# 3-link SessionStart health predicate.
# Checks: .cursor-commands (consumer only), .cursor/plans, and
# ~/.cursor/plugins/local/l9-governance. Realpath-compare, not -L.
# classify_workspace_kind decides ssot / ssot_checkout (no consumer link).
# This is not check_governance_wiring.sh and must not grow into it.
# shellcheck shell=bash

_workspace_link_health_dir() {
  cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
}

if ! declare -F classify_workspace_kind >/dev/null 2>&1; then
  # shellcheck source=workspace_kind.sh
  source "$(_workspace_link_health_dir)/workspace_kind.sh"
fi

workspace_governance_root() {
  printf '%s\n' "${GLOBAL_COMMANDS:-${GOV_ROOT:-$HOME/.cursor-governance}}"
}

workspace_plugin_link() {
  printf '%s\n' "${HOME}/.cursor/plugins/local/l9-governance"
}

# True when $1 is a symlink whose realpath equals $2.
workspace_link_realpath_ok() {
  local link=$1 expected=$2
  [ -L "$link" ] || return 1
  local rt re
  rt="$(python3 -c 'import os,sys; print(os.path.realpath(os.path.expanduser(sys.argv[1])))' "$link" 2>/dev/null || true)"
  re="$(python3 -c 'import os,sys; print(os.path.realpath(os.path.expanduser(sys.argv[1])))' "$expected" 2>/dev/null || true)"
  [ -n "$rt" ] && [ -n "$re" ] && [ "$rt" = "$re" ]
}

# 0 = the three SessionStart links are healthy for this workspace kind.
workspace_links_healthy() {
  local ws="${1:-}"
  [ -n "$ws" ] && [ -d "$ws" ] || return 1
  local kind gc plugin
  kind="$(classify_workspace_kind "$ws")"
  gc="$(workspace_governance_root)"
  plugin="$(workspace_plugin_link)"

  workspace_link_realpath_ok "$plugin" "$gc" || return 1
  workspace_link_realpath_ok "$ws/.cursor/plans" "${HOME}/.cursor/plans" || return 1

  case "$kind" in
    ssot|ssot_checkout)
      if [ -e "$ws/.cursor-commands" ] || [ -L "$ws/.cursor-commands" ]; then
        return 1
      fi
      return 0
      ;;
    *)
      workspace_link_realpath_ok "$ws/.cursor-commands" "$gc"
      ;;
  esac
}
