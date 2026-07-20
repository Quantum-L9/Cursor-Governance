#!/usr/bin/env bash
# Shared SSOT path resolution — source from any governance script.
#
# SSOT: the local GitHub clone at $HOME/.cursor-governance, and ONLY that clone.
# Dropbox is NOT a fallback and is NOT consulted. The clone is created once via
# `git clone https://github.com/Quantum-L9/Cursor-Governance.git ~/.cursor-governance`
# and kept fast-forward-synced every session start by governance_sync.sh. If the
# clone is missing, the fix is to (re-)clone it — never to read from Dropbox.
#
# Layout: repo-root layout only. skills/ commands/ rules/ ops/ + CANONICAL_LAW.md
# live at the clone root, so GLOBAL_COMMANDS == GOV_ROOT == $HOME/.cursor-governance
# (no nested GlobalCommands/ subfolder).
# resolve_governance_paths() exports GOV_ROOT + GLOBAL_COMMANDS.

resolve_governance_paths() {
  GOV_ROOT=""
  GLOBAL_COMMANDS=""
  local root="$HOME/.cursor-governance"
  if [ -d "$root/skills" ] && [ -f "$root/CANONICAL_LAW.md" ]; then
    GOV_ROOT="$root"
    GLOBAL_COMMANDS="$root"
    export GOV_ROOT GLOBAL_COMMANDS
    return 0
  fi
  return 1
}

resolve_governance_paths_or_exit() {
  if resolve_governance_paths; then
    return 0
  fi
  echo "ERROR: governance root not found at \$HOME/.cursor-governance." >&2
  echo "  Fix: git clone https://github.com/Quantum-L9/Cursor-Governance.git \"\$HOME/.cursor-governance\"" >&2
  echo "  Dropbox is not a fallback for this repo; do not read/write governance state there." >&2
  exit 1
}
