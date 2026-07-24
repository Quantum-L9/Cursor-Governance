#!/usr/bin/env bash
# Decide whether a sessionEnd governance backup should run right now.
#
# Cursor fires `sessionEnd` once per composer conversation — including aborted
# chats, scratch windows, and window closes — which on a busy day means a dozen
# `git add -A` + commit + push cycles over the SSOT clone. Several of those land
# mid-build and commit a half-written tree. This gate is the filter the hook
# lacked: it is pure decision logic with no side effects, so it can be fixture
# tested without touching the real clone.
#
# Usage:
#   printf '%s' "$PAYLOAD" | bash ops/scripts/backup_gate.sh "$GLOBAL_COMMANDS"
#
# Exit codes:
#   0   proceed — run the backup
#   10  skip    — reason printed to stdout
#
# Env:
#   GOVERNANCE_BACKUP_FORCE=1        bypass every check below
#   GOVERNANCE_BACKUP_MIN_INTERVAL   debounce window, seconds (default 900)
#   GOVERNANCE_BACKUP_QUIET_SECONDS  required idle time since last write (default 120)
#   GOVERNANCE_BACKUP_STAMP          last-success stamp (default $HOME/.cursor/governance-backup.last)
set -uo pipefail

CLONE="${1:-${GLOBAL_COMMANDS:-$HOME/.cursor-governance}}"
MIN_INTERVAL="${GOVERNANCE_BACKUP_MIN_INTERVAL:-900}"
QUIET_SECONDS="${GOVERNANCE_BACKUP_QUIET_SECONDS:-120}"
STAMP="${GOVERNANCE_BACKUP_STAMP:-$HOME/.cursor/governance-backup.last}"

PROCEED=0
SKIP=10

PAYLOAD=""
if [ ! -t 0 ]; then
  PAYLOAD="$(cat 2>/dev/null || true)"
fi

if [ "${GOVERNANCE_BACKUP_FORCE:-0}" = "1" ]; then
  echo "PROCEED: GOVERNANCE_BACKUP_FORCE=1"
  exit $PROCEED
fi

# --- sessionEnd payload ------------------------------------------------------
# reason ∈ completed|aborted|error|window_close|user_close. An aborted or errored
# conversation says nothing about whether the tree is in a committable state, and
# background agents close constantly, so neither is a backup trigger.
REASON=""
IS_BACKGROUND=""
if [ -n "$PAYLOAD" ] && command -v python3 >/dev/null 2>&1; then
  read -r REASON IS_BACKGROUND <<EOF
$(printf '%s' "$PAYLOAD" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    data = {}
if not isinstance(data, dict):
    data = {}
reason = data.get("reason") or "-"
background = "yes" if data.get("is_background_agent") is True else "no"
print(reason, background)
' 2>/dev/null || echo "- -")
EOF
fi

case "$REASON" in
  aborted|error)
    echo "SKIP: sessionEnd reason=$REASON — not a committable boundary"
    exit $SKIP
    ;;
esac

if [ "$IS_BACKGROUND" = "yes" ]; then
  echo "SKIP: background agent session"
  exit $SKIP
fi

# --- debounce ----------------------------------------------------------------
NOW="$(date +%s 2>/dev/null || echo 0)"
if [ "$NOW" -gt 0 ] && [ -f "$STAMP" ]; then
  LAST="$(cat "$STAMP" 2>/dev/null || echo 0)"
  case "$LAST" in
    ''|*[!0-9]*) LAST=0 ;;
  esac
  if [ "$LAST" -gt 0 ]; then
    AGE=$((NOW - LAST))
    if [ "$AGE" -lt "$MIN_INTERVAL" ]; then
      echo "SKIP: last backup ${AGE}s ago (< ${MIN_INTERVAL}s debounce)"
      exit $SKIP
    fi
  fi
fi

# --- activity guard ----------------------------------------------------------
# If anything in the working tree was written in the last QUIET_SECONDS an agent
# is still mid-edit; committing now snapshots a partial change set.
if command -v python3 >/dev/null 2>&1; then
  IDLE="$(python3 -c '
import os, subprocess, sys, time

clone = sys.argv[1]
try:
    proc = subprocess.run(
        ["git", "-C", clone, "status", "--porcelain", "-z"],
        capture_output=True, text=True, timeout=15,
    )
except Exception:
    print(-1); raise SystemExit
if proc.returncode != 0:
    print(-1); raise SystemExit

entries = [e for e in proc.stdout.split("\0") if e]
newest = 0.0
i = 0
while i < len(entries):
    entry = entries[i]
    i += 1
    if len(entry) < 4:
        continue
    status, path = entry[:2], entry[3:]
    # Renames/copies emit the origin path as the next NUL-separated field.
    if status[0] in ("R", "C"):
        i += 1
    try:
        mtime = os.path.getmtime(os.path.join(clone, path))
    except OSError:
        continue
    newest = max(newest, mtime)

print(int(time.time() - newest) if newest else -1)
' "$CLONE" 2>/dev/null || echo -1)"
  case "$IDLE" in
    ''|*[!0-9-]*) IDLE=-1 ;;
  esac
  if [ "$IDLE" -ge 0 ] && [ "$IDLE" -lt "$QUIET_SECONDS" ]; then
    echo "SKIP: working tree written ${IDLE}s ago (< ${QUIET_SECONDS}s quiet period) — agent likely still editing"
    exit $SKIP
  fi
fi

echo "PROCEED: reason=${REASON:--} gates clear"
exit $PROCEED
