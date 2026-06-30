#!/usr/bin/env bash
# Shared SSOT path resolution — source from any governance script.
#
# SSOT: local GitHub clone at $HOME/.cursor-governance (the whole repo IS GlobalCommands).
# Transition fallback: legacy Dropbox roots (kept until every machine re-clones).
#
# Layout note:
#   - Repo-root layout (GitHub clone): skills/ commands/ rules/ ops/ + CANONICAL_LAW.md live at the
#     clone root, so GLOBAL_COMMANDS == GOV_ROOT == $HOME/.cursor-governance (no nested GlobalCommands/).
#   - Legacy nested layout (Dropbox): GlobalCommands/ is a subfolder of the governance root.
# resolve_governance_paths() detects both and exports GOV_ROOT + GLOBAL_COMMANDS.

resolve_governance_paths() {
  GOV_ROOT=""
  GLOBAL_COMMANDS=""
  for root in \
    "$HOME/.cursor-governance" \
    "$HOME/Dropbox/cursor governance" \
    "$HOME/Dropbox/Cursor Governance"; do
    if [ -d "$root/skills" ] && [ -f "$root/CANONICAL_LAW.md" ]; then
      # Repo-root layout: the clone root itself is GlobalCommands.
      GOV_ROOT="$root"
      GLOBAL_COMMANDS="$root"
      export GOV_ROOT GLOBAL_COMMANDS
      return 0
    elif [ -d "$root/GlobalCommands" ]; then
      # Legacy nested layout (Dropbox).
      GOV_ROOT="$root"
      GLOBAL_COMMANDS="$root/GlobalCommands"
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
  echo "ERROR: governance root not found." >&2
  echo "  Expected (SSOT):   \$HOME/.cursor-governance (clone of Cursor-Governance)" >&2
  echo "  Legacy fallback:   \$HOME/Dropbox/Cursor Governance/GlobalCommands" >&2
  exit 1
}
