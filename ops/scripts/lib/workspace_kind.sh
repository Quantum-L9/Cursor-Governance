#!/usr/bin/env bash
# Classify a workspace as ssot | ssot_checkout | consumer.
# Identity files decide ssot_checkout — not $HOME/.l9/gov-worktrees/ path prefix.
# shellcheck shell=bash

_workspace_kind_realpath() {
  python3 -c 'import os,sys; print(os.path.realpath(os.path.expanduser(sys.argv[1])))' "$1"
}

is_governance_identity_tree() {
  local root="${1:-}"
  [ -n "$root" ] || return 1
  [ -f "$root/CANONICAL_LAW.md" ] || return 1
  [ -f "$root/skills/AUTONOMY_MANIFEST.yaml" ] || return 1
  [ -f "$root/rules/RULES-MANIFEST.yaml" ] || return 1
  [ -f "$root/ops/scripts/check_governance_wiring.sh" ] || return 1
  return 0
}

# Echoes: ssot | ssot_checkout | consumer
classify_workspace_kind() {
  local ws="${1:-}"
  local gc="${GLOBAL_COMMANDS:-${GOV_ROOT:-$HOME/.cursor-governance}}"
  if [ -z "$ws" ]; then
    echo "consumer"
    return 0
  fi
  local ws_real gc_real
  ws_real="$(_workspace_kind_realpath "$ws")"
  gc_real="$(_workspace_kind_realpath "$gc")"
  if [ "$ws_real" = "$gc_real" ]; then
    echo "ssot"
    return 0
  fi
  if is_governance_identity_tree "$ws"; then
    echo "ssot_checkout"
    return 0
  fi
  echo "consumer"
}
