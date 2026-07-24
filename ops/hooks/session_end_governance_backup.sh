#!/usr/bin/env bash
# Cursor sessionEnd hook — backup GlobalCommands to Quantum-L9/Cursor-Governance.
#
# `sessionEnd` fires once per composer conversation (reason ∈ completed|aborted|
# error|window_close|user_close), so it can fire many times an hour while an agent
# is still working. Gating lives in ops/scripts/backup_gate.sh — this hook only
# handles I/O: read the payload, hold a single-flight lock, delegate the decision,
# and stamp a successful backup.
#
# Fail-open: never block session close.
# Path contract: CANONICAL_LAW §9 — resolve via $GLOBAL_COMMANDS, not dirname "$0".
set -uo pipefail

# Read the payload before anything else can consume stdin.
PAYLOAD=""
if [ ! -t 0 ]; then
  PAYLOAD="$(cat 2>/dev/null || true)"
fi

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
RESOLVE="$(dirname "$REAL_HOOK")/../scripts/resolve_governance_paths.sh"
# shellcheck source=../scripts/resolve_governance_paths.sh
source "$RESOLVE"

LOG="${GOVERNANCE_BACKUP_LOG:-$HOME/.cursor-governance/backup.log}"
STAMP="${GOVERNANCE_BACKUP_STAMP:-$HOME/.cursor/governance-backup.last}"
LOCKDIR="${GOVERNANCE_BACKUP_LOCK:-$HOME/.cursor/governance-backup.lock}.d"

mkdir -p "$(dirname "$LOG")" "$(dirname "$STAMP")" "$(dirname "$LOCKDIR")" 2>/dev/null || true

# Keep the log bounded — this hook fires dozens of times a day, forever.
if [ -f "$LOG" ] && [ "$(wc -c <"$LOG" 2>/dev/null || echo 0)" -gt 1048576 ]; then
  tail -n 500 "$LOG" >"$LOG.tmp" 2>/dev/null && mv -f "$LOG.tmp" "$LOG" 2>/dev/null || true
fi

{
  echo "[$(date -Iseconds)] sessionEnd governance backup start"

  if ! resolve_governance_paths; then
    echo "WARN: GLOBAL_COMMANDS unresolved — skipping backup"
    echo "[$(date -Iseconds)] sessionEnd governance backup skipped"
    exit 0
  fi

  # Single-flight: two windows closing together must not race a rebase/push.
  # macOS has no flock, so use an atomic mkdir lock with a stale-breaker.
  if ! mkdir "$LOCKDIR" 2>/dev/null; then
    _now=$(date +%s 2>/dev/null || echo 0)
    _ts=$(cat "$LOCKDIR/ts" 2>/dev/null || echo 0)
    case "$_ts" in ''|*[!0-9]*) _ts=0 ;; esac
    if [ "$_now" -gt 0 ] && [ $((_now - _ts)) -gt 600 ]; then
      rm -rf "$LOCKDIR" 2>/dev/null || true
      mkdir "$LOCKDIR" 2>/dev/null || {
        echo "SKIP: could not acquire lock"
        echo "[$(date -Iseconds)] sessionEnd governance backup skipped"
        exit 0
      }
    else
      echo "SKIP: another backup holds $LOCKDIR"
      echo "[$(date -Iseconds)] sessionEnd governance backup skipped"
      exit 0
    fi
  fi
  date +%s >"$LOCKDIR/ts" 2>/dev/null || true
  trap 'rm -rf "$LOCKDIR" 2>/dev/null || true' EXIT

  GATE="$GLOBAL_COMMANDS/ops/scripts/backup_gate.sh"
  if [ -f "$GATE" ]; then
    GATE_OUT="$(printf '%s' "$PAYLOAD" | bash "$GATE" "$GLOBAL_COMMANDS" 2>&1)"
    GATE_RC=$?
    echo "${GATE_OUT:-gate produced no output}"
    if [ "$GATE_RC" -eq 10 ]; then
      echo "[$(date -Iseconds)] sessionEnd governance backup skipped"
      exit 0
    fi
  else
    echo "WARN: backup_gate.sh missing — proceeding ungated"
  fi

  BACKUP="$GLOBAL_COMMANDS/ops/scripts/backup_to_github.sh"
  if [ -x "$BACKUP" ]; then
    if bash "$BACKUP" "chore(governance): session-end sync $(date +%Y-%m-%d)"; then
      date +%s >"$STAMP" 2>/dev/null || true
    else
      echo "WARN: backup exited non-zero"
    fi
  else
    echo "WARN: backup script missing or not executable: $BACKUP"
  fi

  echo "[$(date -Iseconds)] sessionEnd governance backup done"
} >>"$LOG" 2>&1

exit 0
