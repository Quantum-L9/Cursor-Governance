#!/usr/bin/env bash
# L9_SESSION_START_WRAPPER=1
# Thin SessionStart wrapper. Doctrine/profile/autonomy logic lives only in:
#   environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh
#
# Committed at <repo>/.claude/hooks/session_start_claude_governance.sh so Web/Mobile
# have a git-tracked entrypoint. This file must stay a wrapper — never a copy of
# the brain. Reconcile copies this template to that consumer path.
#
# Contract: FAIL-OPEN. Always exit 0.
set -uo pipefail

WORKSPACE="${CLAUDE_PROJECT_DIR:-$PWD}"
REL="environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh"

for f in "$WORKSPACE/$REL" "$HOME/.cursor-governance/$REL"; do
  case "$f" in
    */.claude/hooks/*) continue ;;
  esac
  if [ -f "$f" ]; then
    exec bash "$f"
  fi
done

printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"L9 Governance — SessionStart wrapper: SSOT hook not found; continue without bootstrap"}}'
exit 0
