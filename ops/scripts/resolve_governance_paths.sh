#!/usr/bin/env bash
# Shared SSOT path resolution — source from any governance script.
# Canonical law: $HOME/Dropbox/Cursor Governance/CANONICAL_LAW.md

resolve_governance_paths() {
  GOV_ROOT=""
  GLOBAL_COMMANDS=""
  for p in "$HOME/Dropbox/cursor governance" "$HOME/Dropbox/Cursor Governance"; do
    if [ -d "$p/GlobalCommands" ]; then
      GOV_ROOT=$p
      GLOBAL_COMMANDS="$p/GlobalCommands"
      export GOV_ROOT GLOBAL_COMMANDS
      return 0
    fi
  done
  return 1
}

resolve_governance_paths_or_exit() {
  if resolve_governance_paths; then
    return 0
  fi
  echo "ERROR: Dropbox governance root not found." >&2
  echo "  Expected: \$HOME/Dropbox/Cursor Governance/GlobalCommands" >&2
  exit 1
}
