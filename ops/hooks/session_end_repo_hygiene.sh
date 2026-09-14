#!/usr/bin/env bash
# RETIRED — sessionEnd must not dirt-close or auto-hygiene.
#
# Dirt-close swept every novel porcelain path in the payload workspace and
# removed those files from the tree. That scooped other chats on a shared
# clone. sessionEnd no longer invokes this script (hooks.json.template plus
# setup_workspace_symlinks.sh retire strip). If a stale hooks.json still
# lists ./hooks/session-end-repo-hygiene.sh, this file is a no-op.
#
# On-demand only (never from sessionEnd):
#   python3 ops/scripts/session_end_dirt_close.py --workspace "$WS" --status
#   python3 ops/scripts/repo_hygiene.py --workspace "$WS" --apply
#
# Fail-open: never block session close.
set -uo pipefail

if [ ! -t 0 ]; then
  cat >/dev/null 2>&1 || true
fi

LOG="${L9_REPO_HYGIENE_LOG:-$HOME/.cursor-governance/hygiene.log}"
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
echo "[$(date -Iseconds)] sessionEnd repo hygiene RETIRED — no-op" >>"$LOG" 2>/dev/null || true
exit 0
