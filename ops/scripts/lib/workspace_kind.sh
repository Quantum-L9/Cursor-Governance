#!/usr/bin/env bash
# Classify a workspace as ssot | ssot_checkout | consumer.
# Identity files decide ssot_checkout — not $HOME/.l9/gov-worktrees/ path prefix.
# shellcheck shell=bash

# Builtins only: callers run under minimal PATHs (a gate test uses
# PATH=/usr/bin:/bin), where python3 may be absent. An interpreter failure here
# used to yield "" for both sides, and "" = "" classified every workspace ssot.
# cd -P / pwd -P resolves symlinks (macOS /tmp -> /private/tmp) as before; a path
# that is not an existing directory is returned as given, so it can never equal
# a resolved one by accident.
_workspace_kind_realpath() {
  local p="${1:-}"
  case "$p" in
    \~) p="$HOME" ;;
    \~/*) p="$HOME/${p#\~/}" ;;
  esac
  if [ -n "$p" ] && [ -d "$p" ]; then
    (cd -P -- "$p" 2>/dev/null && pwd -P) || printf '%s\n' "$p"
  else
    printf '%s\n' "$p"
  fi
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
# Never use GOV_ROOT here: callers (run_pr_gate.sh) overwrite it to the
# workspace under test, which would mis-classify a worktree as ssot.
classify_workspace_kind() {
  local ws="${1:-}"
  local gc="${GLOBAL_COMMANDS:-}"
  if [ -z "$gc" ]; then
    if declare -F resolve_governance_paths >/dev/null 2>&1 && resolve_governance_paths; then
      gc="$GLOBAL_COMMANDS"
    else
      gc="$HOME/.cursor-governance"
    fi
  fi
  if [ -z "$ws" ]; then
    echo "consumer"
    return 0
  fi
  local ws_real gc_real
  ws_real="$(_workspace_kind_realpath "$ws")"
  gc_real="$(_workspace_kind_realpath "$gc")"
  if [ -n "$ws_real" ] && [ "$ws_real" = "$gc_real" ]; then
    echo "ssot"
    return 0
  fi
  if is_governance_identity_tree "$ws"; then
    echo "ssot_checkout"
    return 0
  fi
  echo "consumer"
}
