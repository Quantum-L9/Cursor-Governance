#!/usr/bin/env bash
# Cursor sessionEnd hook — backup GlobalCommands to Quantum-L9/Cursor-Governance.
# Fail-open: never block session close.
# Path contract: CANONICAL_LAW §9 — resolve via $GLOBAL_COMMANDS, not dirname "$0".
set -uo pipefail

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
RESOLVE="$(dirname "$REAL_HOOK")/../scripts/resolve_governance_paths.sh"
# shellcheck source=../scripts/resolve_governance_paths.sh
source "$RESOLVE"

LOG="${GOVERNANCE_BACKUP_LOG:-$HOME/.cursor-governance/backup.log}"
BACKUP=""

mkdir -p "$(dirname "$LOG")"

{
  echo "[$(date -Iseconds)] sessionEnd governance backup start"
  if resolve_governance_paths; then
    BACKUP="$GLOBAL_COMMANDS/ops/scripts/backup_to_github.sh"
  fi
  if [ -n "$BACKUP" ] && [ -x "$BACKUP" ]; then
    bash "$BACKUP" "chore(governance): session-end sync $(date +%Y-%m-%d)" || echo "WARN: backup exited non-zero"
  else
    echo "WARN: backup script missing or not executable: ${BACKUP:-<GLOBAL_COMMANDS unresolved>}"
  fi
  echo "[$(date -Iseconds)] sessionEnd governance backup done"
} >>"$LOG" 2>&1

exit 0
