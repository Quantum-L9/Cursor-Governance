#!/usr/bin/env bash
# Cursor sessionEnd hook — park THIS conversation's authored bytes only.
#
# Does not call backup_to_github.sh (that script `git add -A`s the SSOT and
# would scoop other chats). Operator push stays `make backup`.
# Does not read porcelain. Paths come from the session authored ledger
# (`postToolUse` → session_authored_paths.py). Empty ledger → skip.
# Never deletes worktree files. Never walks sibling worktrees.
#
# Fail-open: never block session close.
# Path contract: CANONICAL_LAW §9 — resolve via $GLOBAL_COMMANDS, not dirname "$0".
set -uo pipefail

PAYLOAD=""
if [ ! -t 0 ]; then
  PAYLOAD="$(cat 2>/dev/null || true)"
fi

if [ "${L9_SESSION_PRESERVE:-1}" = "0" ] || [ "${GOVERNANCE_BACKUP_SKIP:-0}" = "1" ]; then
  exit 0
fi

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
RESOLVE="$(dirname "$REAL_HOOK")/../scripts/resolve_governance_paths.sh"
# shellcheck source=../scripts/resolve_governance_paths.sh
source "$RESOLVE"

LOG="${L9_SESSION_PRESERVE_LOG:-$HOME/.cursor/l9/session-preserve.log}"
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true

if [ -f "$LOG" ] && [ "$(wc -c <"$LOG" 2>/dev/null || echo 0)" -gt 1048576 ]; then
  tail -n 500 "$LOG" >"$LOG.tmp" 2>/dev/null && mv -f "$LOG.tmp" "$LOG" 2>/dev/null || true
fi

{
  echo "[$(date -Iseconds)] sessionEnd preserve start"

  if ! resolve_governance_paths; then
    echo "WARN: GLOBAL_COMMANDS unresolved — skipping preserve"
    echo "[$(date -Iseconds)] sessionEnd preserve skipped"
    exit 0
  fi

  PRESERVE="$GLOBAL_COMMANDS/ops/scripts/session_end_preserve.py"
  if [ ! -f "$PRESERVE" ]; then
    PRESERVE="$(dirname "$REAL_HOOK")/../scripts/session_end_preserve.py"
  fi
  if [ ! -f "$PRESERVE" ]; then
    echo "WARN: session_end_preserve.py missing"
    exit 0
  fi

  PY="$GLOBAL_COMMANDS/.venv/bin/python"
  [ -x "$PY" ] || PY="python3"

  printf '%s' "$PAYLOAD" | "$PY" "$PRESERVE" || echo "WARN: preserve exited non-zero"

  echo "[$(date -Iseconds)] sessionEnd preserve done"
} >>"$LOG" 2>&1

exit 0
