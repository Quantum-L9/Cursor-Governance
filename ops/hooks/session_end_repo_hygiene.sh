#!/usr/bin/env bash
# Cursor sessionEnd hook — delete local git residue whose content already landed.
#
# Removes the standing friction of stale branches, spent per-PR worktrees, and
# stashes nobody pops, without anyone having to ask for it. Every deletion is
# preceded by a preserve ref under refs/l9/preserved/, so the safe answer and
# the automatic answer are the same answer. See ops/scripts/repo_hygiene.py.
#
# Runs last in the sessionEnd chain: governance-backup.sh commits and pushes
# first, so a branch is only judged after its work has had its chance to land.
#
# Dirt-close runs before --apply: classify porcelain, drop landed copies,
# park novel unique onto l9/dirt-shelf, prune absorbed parks. Kill switch:
# L9_HYGIENE_DIRT_CLOSE=0. Hygiene kill switch: L9_REPO_HYGIENE=0.
# Fail-open: never block session close.
# Path contract: CANONICAL_LAW §9 — resolve via $GLOBAL_COMMANDS, not dirname "$0".
set -uo pipefail

PAYLOAD=""
if [ ! -t 0 ]; then
  PAYLOAD="$(cat 2>/dev/null || true)"
fi

if [ "${L9_REPO_HYGIENE:-1}" = "0" ]; then
  exit 0
fi

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
RESOLVE="$(dirname "$REAL_HOOK")/../scripts/resolve_governance_paths.sh"
# shellcheck source=../scripts/resolve_governance_paths.sh
source "$RESOLVE"

LOG="${L9_REPO_HYGIENE_LOG:-$HOME/.cursor-governance/hygiene.log}"
LOCKDIR="${L9_REPO_HYGIENE_LOCK:-$HOME/.cursor/repo-hygiene.lock}.d"
mkdir -p "$(dirname "$LOG")" "$(dirname "$LOCKDIR")" 2>/dev/null || true

if [ -f "$LOG" ] && [ "$(wc -c <"$LOG" 2>/dev/null || echo 0)" -gt 1048576 ]; then
  tail -n 500 "$LOG" >"$LOG.tmp" 2>/dev/null && mv -f "$LOG.tmp" "$LOG" 2>/dev/null || true
fi

# The session's own workspace, so this also cleans consumer repos — not just the
# governance clone. Falls back to the resolved SSOT when the payload is silent.
workspace_from_payload() {
  printf '%s' "$PAYLOAD" | python3 -c '
import json, sys
try:
    event = json.load(sys.stdin)
except Exception:
    sys.exit(0)
roots = event.get("workspace_roots") or []
candidate = roots[0] if roots else (event.get("workspace") or event.get("cwd") or "")
print(candidate or "")
' 2>/dev/null || true
}

{
  echo "[$(date -Iseconds)] sessionEnd repo hygiene start"

  if ! resolve_governance_paths; then
    echo "WARN: GLOBAL_COMMANDS unresolved — skipping hygiene"
    exit 0
  fi

  # sessionEnd fires once per conversation; concurrent windows must not race
  # two `git worktree remove` passes against the same repo.
  if ! mkdir "$LOCKDIR" 2>/dev/null; then
    _now=$(date +%s 2>/dev/null || echo 0)
    _ts=$(cat "$LOCKDIR/ts" 2>/dev/null || echo 0)
    case "$_ts" in '' | *[!0-9]*) _ts=0 ;; esac
    if [ "$_now" -gt 0 ] && [ $((_now - _ts)) -gt 600 ]; then
      rm -rf "$LOCKDIR" 2>/dev/null || true
      mkdir "$LOCKDIR" 2>/dev/null || { echo "SKIP: could not acquire lock"; exit 0; }
    else
      echo "SKIP: another hygiene pass holds $LOCKDIR"
      exit 0
    fi
  fi
  date +%s >"$LOCKDIR/ts" 2>/dev/null || true
  trap 'rm -rf "$LOCKDIR" 2>/dev/null || true' EXIT

  WS="$(workspace_from_payload)"
  [ -n "$WS" ] && [ -d "$WS" ] || WS="$GLOBAL_COMMANDS"

  HYGIENE="$GLOBAL_COMMANDS/ops/scripts/repo_hygiene.py"
  if [ ! -f "$HYGIENE" ]; then
    echo "WARN: repo_hygiene.py missing: $HYGIENE"
    exit 0
  fi

  PY="$GLOBAL_COMMANDS/.venv/bin/python"
  [ -x "$PY" ] || PY="python3"

  RECEIPTS="$WS/.l9/hygiene"
  mkdir -p "$RECEIPTS" 2>/dev/null || RECEIPTS=""
  MODE="${L9_REPO_HYGIENE_MODE:---apply}"

  echo "workspace: $WS (mode $MODE)"

  DIRT_CLOSE="$GLOBAL_COMMANDS/ops/scripts/session_end_dirt_close.py"
  if [ "${L9_HYGIENE_DIRT_CLOSE:-1}" != "0" ] && [ -f "$DIRT_CLOSE" ]; then
    DIRT_OUT="$RECEIPTS/dirt-close-hook.json"
    [ -n "$RECEIPTS" ] || DIRT_OUT="/dev/null"
    printf '%s' "$PAYLOAD" | "$PY" "$DIRT_CLOSE" --workspace "$WS" --apply >"$DIRT_OUT" 2>>"$LOG" || {
      echo "WARN: dirt-close exited non-zero"
    }
    if [ -n "$RECEIPTS" ] && [ -f "$DIRT_OUT" ]; then
      "$PY" - "$DIRT_OUT" <<'DIRTSUM' 2>/dev/null || true
import json, sys
doc = json.load(open(sys.argv[1]))
st = doc.get("status") or doc
print(
    "dirt-close dirty_unique=%s already_landed=%s novel_parked=%s absorbed_pruned=%s skip=%s"
    % (
        st.get("dirty_unique", len(st.get("dirty_files") or [])),
        len(st.get("already_landed") or []),
        len(st.get("novel_parked") or []),
        len(st.get("absorbed_pruned") or []),
        st.get("skipped") or doc.get("skip") or "",
    )
)
DIRTSUM
    fi
  else
    echo "dirt-close skipped (L9_HYGIENE_DIRT_CLOSE=0 or script missing)"
  fi

  if [ -n "$RECEIPTS" ]; then
    RECEIPT="$RECEIPTS/$(date -u +%Y%m%dT%H%M%SZ).json"
    "$PY" "$HYGIENE" --workspace "$WS" "$MODE" --json >"$RECEIPT" 2>>"$LOG" || {
      echo "WARN: hygiene exited non-zero"
      exit 0
    }
    "$PY" - "$RECEIPT" <<'SUMMARY' 2>/dev/null || true
import json, sys
report = json.load(open(sys.argv[1]))
def count(rows, key, *values):
    return sum(1 for row in rows if row[key] in values)
print(
    "deleted branches=%d removed worktrees=%d dropped stashes=%d preserved refs=%d"
    % (
        count(report["branches"], "action", "delete"),
        count(report["worktrees"], "action", "remove"),
        count(report["stashes"], "action", "preserve+drop"),
        len(report["preserved_refs"]),
    )
)
for row in report["branches"]:
    if row["status"] in {"closed_unlanded", "reused_after_merge"}:
        print("UNLANDED: %s — %s — recover from %s" % (row["name"], row["detail"], row["tip"][:12]))
for err in report["errors"]:
    print("ERROR: %s" % err)
SUMMARY
  else
    "$PY" "$HYGIENE" --workspace "$WS" "$MODE" || echo "WARN: hygiene exited non-zero"
  fi

  echo "[$(date -Iseconds)] sessionEnd repo hygiene done"
} >>"$LOG" 2>&1

exit 0
