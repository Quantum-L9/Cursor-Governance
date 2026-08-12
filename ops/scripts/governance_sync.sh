#!/usr/bin/env bash
# Guarded BIDIRECTIONAL auto-sync for the ~/.cursor-governance SSOT clone.
#
# NOTE (sessionStart): Cursor sessionStart does NOT use this script's pull-half.
# Tip activation on session start is `governance_activate_fresh.sh` (foreground
# ff-or-swap). Keep this file for manual/`make` sync and for its push-half
# (backup_to_github.sh), which the activator may call pre-swap. Do not reintroduce
# dual pull strategies on sessionStart.
#
# Replaces the unsafe `git fetch && git reset --hard origin/main` pattern.
#
# Bootstrap (fresh machine):
#   - If $CLONE isn't a git repo yet, clone it from GOVERNANCE_GITHUB_REMOTE
#     (default: Quantum-L9/Cursor-Governance) before attempting to sync.
#
# Pull half (remote -> local):
#   - NEVER destroys local edits: fast-forward only; if the tree is dirty, stash -> ff -> pop.
# Push half (local -> remote):
#   - Delegates to backup_to_github.sh, the same script sessionEnd uses, so local work
#     reaches GitHub at session START too — not only on a clean session close. Reusing it
#     inherits all its guards (refuses unmerged paths, staged conflict markers, stale
#     uv.lock; rebases onto origin/main and aborts rather than pushing a conflicted tree).
#     Disable with GOVERNANCE_SYNC_PUSH=0.
#
# Also:
#   - Single-flight: flock prevents concurrent runs when multiple Cursor windows open at once.
#     The lock is held across BOTH halves so a start-sync and an end-backup can't interleave.
#   - Self-heal: re-copies the installed session-start bootstrap when the source changes,
#     so sync-logic updates actually propagate (the installed hook is a real file, not a symlink).
#   - Fail-soft: every step tolerates failure (offline, no upstream) and exits 0. Failures that
#     need a human are announced on stderr, never swallowed.
#
# Opt-in hard reset: set GOVERNANCE_SYNC_HARD_RESET=1 to mirror remote exactly (discards local).
set -uo pipefail

CLONE="${CURSOR_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
BRANCH="${GOVERNANCE_GITHUB_BRANCH:-main}"
LOCK="$HOME/.cursor/governance-sync.lock"
REMOTE="${GOVERNANCE_GITHUB_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"

command -v git >/dev/null 2>&1 || exit 0
mkdir -p "$(dirname "$LOCK")" 2>/dev/null || true

# Single-flight: if another window holds the lock, skip silently. Acquired
# BEFORE the clone-if-missing bootstrap below so two windows racing on a
# fresh machine can't both `git clone` into the same path at once.
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

# Guarded clone-if-missing: bootstraps the SSOT clone on a fresh machine so a
# freshly-cloned consumer repo can wire governance without a manual `git clone`
# step first. Only fires when $CLONE isn't a git repo yet — never touches an
# existing clone's remote/branch config. Fail-soft like every other guard here:
# a failed clone just skips sync for this run (exit 0), it never aborts loudly.
# Runs inside the lock above, so concurrent windows can't race the clone.
if [ ! -d "$CLONE/.git" ]; then
  if [ -e "$CLONE" ] && [ ! -d "$CLONE" ]; then
    echo "WARNING: governance_sync.sh: $CLONE exists and is not a directory — skipping clone." >&2
    exit 0
  fi
  echo "NOTE: governance_sync.sh: $CLONE missing — cloning $REMOTE" >&2
  if ! git clone --quiet --branch "$BRANCH" "$REMOTE" "$CLONE" 2>/dev/null; then
    echo "WARNING: governance_sync.sh: clone of $REMOTE failed — governance not bootstrapped." >&2
    exit 0
  fi
fi

cd "$CLONE" || exit 0

git fetch --quiet origin "$BRANCH" 2>/dev/null || exit 0
git rev-parse "origin/$BRANCH" >/dev/null 2>&1 || exit 0

if [ "${GOVERNANCE_SYNC_HARD_RESET:-0}" = "1" ]; then
  git reset --hard "origin/$BRANCH" >/dev/null 2>&1 || true
elif git diff --quiet && git diff --cached --quiet; then
  # Clean tree -> safe fast-forward. A failure here means local commits have diverged
  # from origin/BRANCH; the push half below rebases and resolves it, so only announce.
  if ! git merge --ff-only --quiet "origin/$BRANCH" >/dev/null 2>&1; then
    echo "NOTE: governance_sync.sh: cannot fast-forward $CLONE onto origin/$BRANCH (local commits diverged). Push half will rebase." >&2
  fi
else
  # Dirty tree -> preserve local edits across the fast-forward.
  if git stash push -q -u -m governance-autosync >/dev/null 2>&1; then
    git merge --ff-only --quiet "origin/$BRANCH" >/dev/null 2>&1 || true
    if ! git stash pop -q >/dev/null 2>&1; then
      # `git stash pop` does a real 3-way merge on reapply. On conflict it can write
      # literal <<<<<<< / ======= / >>>>>>> markers straight into the working tree and
      # mark those paths unmerged, while also leaving the stash intact. Silencing this
      # to /dev/null is exactly how those markers end up baked into a real commit by
      # the next automated backup — so make it loud and discoverable instead of
      # swallowing it. Still fail-soft: this script always exits 0 either way.
      if git status --porcelain 2>/dev/null | grep -qE '^(UU|AA|DD|AU|UA|UD|DU) '; then
        {
          echo "=== governance_sync.sh: stash-pop conflict at $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
          git status --porcelain 2>/dev/null | grep -E '^(UU|AA|DD|AU|UA|UD|DU) '
        } >> "$CLONE/.sync-conflict" 2>/dev/null
        echo "WARNING: governance_sync.sh: 'git stash pop' left unresolved conflict markers/unmerged paths in $CLONE. Resolve before the next commit (see $CLONE/.sync-conflict). Stash was NOT dropped." >&2
      fi
    fi
  fi
fi

# ── Push half: local -> GitHub ────────────────────────────────────────────────
# Without this, local work only reaches GitHub on a clean session END — a crash, a
# force-quit, or a hook timeout leaves it unpushed indefinitely. backup_to_github.sh
# is intentionally reused rather than reimplemented: one push implementation, no drift.
# It is a no-op (exit 0, "nothing to commit") when the tree already matches the index.
if [ "${GOVERNANCE_SYNC_PUSH:-1}" = "1" ] && [ "${GOVERNANCE_SYNC_HARD_RESET:-0}" != "1" ]; then
  PUSH="$CLONE/ops/scripts/backup_to_github.sh"
  if [ -x "$PUSH" ]; then
    PUSH_OUT="$(bash "$PUSH" "chore(governance): session-start sync $(date +%Y-%m-%d\ %H:%M)" 2>&1)" || {
      echo "WARNING: governance_sync.sh: push to origin/$BRANCH failed — local work is NOT backed up. Resolve manually:" >&2
      echo "$PUSH_OUT" | tail -5 >&2
    }
  fi
fi

# Self-heal the installed bootstrap hook (real file copied by setup_workspace_symlinks.sh).
src="$CLONE/ops/hooks/session_start_bootstrap.sh"
dst="$HOME/.cursor/hooks/session-start-bootstrap.sh"
if [ -f "$src" ] && [ -f "$dst" ] && ! cmp -s "$src" "$dst"; then
  cp -f "$src" "$dst" 2>/dev/null && chmod +x "$dst" 2>/dev/null || true
fi

exit 0
