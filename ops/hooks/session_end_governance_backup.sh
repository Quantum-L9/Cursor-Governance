#!/usr/bin/env bash
# Cursor sessionEnd hook — backup GlobalCommands to cryptoxdog/Cursor-Governance.
# Fail-open: never block session close.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP="$SCRIPT_DIR/../scripts/backup_to_github.sh"
LOG="${GOVERNANCE_BACKUP_LOG:-$HOME/.cursor-governance/backup.log}"

mkdir -p "$(dirname "$LOG")"

{
  echo "[$(date -Iseconds)] sessionEnd governance backup start"
  if [ -x "$BACKUP" ]; then
    bash "$BACKUP" "chore(governance): session-end sync $(date +%Y-%m-%d)" || echo "WARN: backup exited non-zero"
  else
    echo "WARN: backup script missing: $BACKUP"
  fi
  echo "[$(date -Iseconds)] sessionEnd governance backup done"
} >>"$LOG" 2>&1

exit 0
