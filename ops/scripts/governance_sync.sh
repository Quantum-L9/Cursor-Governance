#!/usr/bin/env bash
# Guarded auto-sync for the ~/.cursor-governance SSOT clone.
#
# Replaces the unsafe `git fetch && git reset --hard origin/main` pattern.
# Guarantees:
#   - NEVER destroys local edits: fast-forward only; if the tree is dirty, stash -> ff -> pop.
#   - Single-flight: flock prevents concurrent runs when multiple Cursor windows open at once.
#   - Self-heal: re-copies the installed session-start bootstrap when the source changes,
#     so sync-logic updates actually propagate (the installed hook is a real file, not a symlink).
#   - Fail-soft: every step tolerates failure (offline, no upstream) and exits 0.
#
# Opt-in hard reset: set GOVERNANCE_SYNC_HARD_RESET=1 to mirror remote exactly (discards local).
set -uo pipefail

CLONE="${CURSOR_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
BRANCH="${GOVERNANCE_GITHUB_BRANCH:-main}"
LOCK="$HOME/.cursor/governance-sync.lock"

[ -d "$CLONE/.git" ] || exit 0          # only sync a real git clone
command -v git >/dev/null 2>&1 || exit 0
mkdir -p "$(dirname "$LOCK")" 2>/dev/null || true

# Single-flight: if another window holds the lock, skip silently.
# Use flock where available; macOS has no flock, so fall back to an atomic mkdir lock.
if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK" 2>/dev/null || exit 0
  flock -n 9 || exit 0
else
  # macOS has no flock: atomic mkdir lock with a portable timestamp stale-breaker
  # (uses only `date +%s`, so no GNU/BSD find/stat flag differences).
  LOCKDIR="${LOCK}.d"
  if ! mkdir "$LOCKDIR" 2>/dev/null; then
    # Lock held — break it only if clearly stale (>5 min, e.g. a killed run), else skip.
    _now=$(date +%s 2>/dev/null || echo 0)
    _ts=$(cat "$LOCKDIR/ts" 2>/dev/null || echo 0)
    if [ "$_now" -gt 0 ] && [ $((_now - _ts)) -gt 300 ]; then
      rm -rf "$LOCKDIR" 2>/dev/null || true
      mkdir "$LOCKDIR" 2>/dev/null || exit 0
    else
      exit 0
    fi
  fi
  date +%s > "$LOCKDIR/ts" 2>/dev/null || true
  trap 'rm -rf "$LOCKDIR" 2>/dev/null || true' EXIT
fi

cd "$CLONE" || exit 0

git fetch --quiet origin "$BRANCH" 2>/dev/null || exit 0
git rev-parse "origin/$BRANCH" >/dev/null 2>&1 || exit 0

if [ "${GOVERNANCE_SYNC_HARD_RESET:-0}" = "1" ]; then
  git reset --hard "origin/$BRANCH" >/dev/null 2>&1 || true
elif git diff --quiet && git diff --cached --quiet; then
  # Clean tree -> safe fast-forward.
  git merge --ff-only --quiet "origin/$BRANCH" >/dev/null 2>&1 || true
else
  # Dirty tree -> preserve local edits across the fast-forward.
  if git stash push -q -u -m governance-autosync >/dev/null 2>&1; then
    git merge --ff-only --quiet "origin/$BRANCH" >/dev/null 2>&1 || true
    git stash pop -q >/dev/null 2>&1 || true   # conflict leaves stash intact for manual resolve
  fi
fi

# Self-heal the installed bootstrap hook (real file copied by setup_workspace_symlinks.sh).
src="$CLONE/ops/hooks/session_start_bootstrap.sh"
dst="$HOME/.cursor/hooks/session-start-bootstrap.sh"
if [ -f "$src" ] && [ -f "$dst" ] && ! cmp -s "$src" "$dst"; then
  cp -f "$src" "$dst" 2>/dev/null && chmod +x "$dst" 2>/dev/null || true
fi

exit 0
