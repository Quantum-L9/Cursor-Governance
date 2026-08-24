#!/usr/bin/env bash
# In-place catch-up for a named Cursor-Governance clone.
# Never deletes unique bytes. Parks unique commits, every dirty tracked
# path, and untracked copies that origin now tracks. Then `git reset --keep`.
# Never stash -u. Never activate_fresh. Never reset --hard as the catch-up.
set -euo pipefail

# Inherit no host git dir — `git -C` is ignored when GIT_DIR is set.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_COMMON_DIR GIT_PREFIX

CLONE="${CURSOR_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
CLONE="$(cd "$CLONE" && pwd)"
TARGET_BRANCH="${GOVERNANCE_GITHUB_BRANCH:-main}"

export GOVERNANCE_SYNC_PUSH=0
export GOVERNANCE_SYNC_HARD_RESET=0

if [ ! -e "$CLONE/.git" ]; then
  echo "FAIL: $CLONE is not a git clone." >&2
  exit 1
fi

GITDIR_BEFORE="$(git -C "$CLONE" rev-parse --git-common-dir)"
BRANCH_BEFORE="$(git -C "$CLONE" rev-parse --abbrev-ref HEAD)"
HEAD_BEFORE="$(git -C "$CLONE" rev-parse HEAD)"

if [ "$BRANCH_BEFORE" != "$TARGET_BRANCH" ]; then
  echo "FAIL: /ff catch-up to origin/${TARGET_BRANCH} only runs on '${TARGET_BRANCH}' (this clone is '${BRANCH_BEFORE}'). Unique feature work stays. Do not reset a feature branch onto main." >&2
  exit 1
fi

VENV_BEFORE=""
if [ -e "$CLONE/.venv" ]; then
  VENV_BEFORE="$(cd "$CLONE/.venv" && pwd -P)"
fi

UNTRACKED_BEFORE="$(git -C "$CLONE" ls-files --others --exclude-standard | LC_ALL=C sort)"

echo "ff: clone=$CLONE branch=$BRANCH_BEFORE push=0 hard_reset=0 stash_u=0"
echo "ff: keeping .venv and untracked; unique commits and dirty tracked get preserve refs"

git -C "$CLONE" fetch --quiet origin "$TARGET_BRANCH"
if ! git -C "$CLONE" rev-parse --verify "origin/$TARGET_BRANCH" >/dev/null 2>&1; then
  echo "FAIL: origin/${TARGET_BRANCH} missing after fetch." >&2
  exit 1
fi

AHEAD="$(git -C "$CLONE" rev-list --count "origin/${TARGET_BRANCH}..HEAD")"
BEHIND="$(git -C "$CLONE" rev-list --count "HEAD..origin/${TARGET_BRANCH}")"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PRESERVE_BRANCH=""
DIRTY_REF=""
HOLD=""
CLONE_KEY="$(printf '%s' "$CLONE" | shasum -a 256 | awk '{print substr($1,1,12)}')"
HOLD_ROOT="${HOME}/.cursor/l9-ff-hold/${CLONE_KEY}/${STAMP}"

if [ "$AHEAD" -gt 0 ]; then
  PRESERVE_REF="refs/l9/preserved/ff/${STAMP}"
  PRESERVE_BRANCH="l9/ff-preserve-${STAMP}"
  git -C "$CLONE" update-ref "$PRESERVE_REF" HEAD
  git -C "$CLONE" branch "$PRESERVE_BRANCH" HEAD
  echo "OK: preserved ${AHEAD} unique commit(s) at ${PRESERVE_BRANCH} (${PRESERVE_REF})"
fi

# All dirty tracked paths block `reset --keep` ("not uptodate"), including
# files origin did not touch and clones with no merge-base. Do not use
# a triple-dot vs origin — that fails on unrelated history and misses
# non-overlapping dirt.
DIRTY_TRACKED="$(git -C "$CLONE" diff --name-only HEAD | LC_ALL=C sort | sed '/^$/d' || true)"

_blob_at() {
  git -C "$CLONE" rev-parse "${1}:${2}" 2>/dev/null || true
}

_wt_blob() {
  local rel="$1"
  if [ -e "$CLONE/$rel" ] || [ -L "$CLONE/$rel" ]; then
    git -C "$CLONE" hash-object -- "$rel" 2>/dev/null || true
  else
    printf ''
  fi
}

_copy_hold_tracked() {
  local rel="$1"
  local dest="$HOLD_ROOT/tracked/$rel"
  mkdir -p "$(dirname "$dest")"
  if [ -e "$CLONE/$rel" ] || [ -L "$CLONE/$rel" ]; then
    cp -a "$CLONE/$rel" "$dest"
  else
    printf '%s\n' "__deleted__" >"${dest}.deleted"
  fi
}

if [ -n "$DIRTY_TRACKED" ]; then
  if [ "$BEHIND" -eq 0 ] && [ "$AHEAD" -eq 0 ]; then
    echo "OK: already at origin/${TARGET_BRANCH}; leaving unique dirty tracked in the worktree"
    echo "$DIRTY_TRACKED" | while IFS= read -r rel; do
      [ -z "$rel" ] && continue
      echo "ff: classify path=${rel} class=leave_at_tip"
    done
  else
    mkdir -p "$HOLD_ROOT/tracked"
    HOLD="$HOLD_ROOT"
    DIRTY_SHA="$(git -C "$CLONE" stash create)"
    if [ -z "$DIRTY_SHA" ]; then
      echo "FAIL: dirty tracked files exist but stash create produced no object." >&2
      exit 1
    fi
    DIRTY_REF="refs/l9/preserved/ff-dirty/${STAMP}"
    git -C "$CLONE" update-ref "$DIRTY_REF" "$DIRTY_SHA"
    echo "OK: parked dirty-tracked at ${DIRTY_REF} (${DIRTY_SHA:0:12})"

    while IFS= read -r rel; do
      [ -z "$rel" ] && continue
      origin_blob="$(_blob_at "origin/${TARGET_BRANCH}" "$rel")"
      wt_blob="$(_wt_blob "$rel")"
      if [ -n "$origin_blob" ] && [ "$wt_blob" = "$origin_blob" ]; then
        class="already_at_origin"
      else
        class="unique"
      fi
      echo "ff: classify path=${rel} class=${class}"
      _copy_hold_tracked "$rel"
      if git -C "$CLONE" cat-file -e "HEAD:${rel}" 2>/dev/null; then
        git -C "$CLONE" restore --source=HEAD --staged --worktree -- "$rel"
      else
        git -C "$CLONE" restore --staged -- "$rel" 2>/dev/null || true
      fi
    done <<<"$DIRTY_TRACKED"
    echo "OK: dirty-tracked copies also at ${HOLD_ROOT}/tracked (never deleted)"
  fi
fi

# origin/main may now track a path that is still untracked here. reset --keep
# may leave that worktree copy untouched. Walk origin's tree — do not depend
# on `comm` + `ls-files --others` (untracked-cache / excludesfile miss paths
# on some CI images).
OVERWRITE_UNTRACKED=""
while IFS= read -r rel; do
  [ -z "$rel" ] && continue
  if git -C "$CLONE" ls-files --error-unmatch -- "$rel" >/dev/null 2>&1; then
    continue
  fi
  if [ -e "$CLONE/$rel" ] || [ -L "$CLONE/$rel" ]; then
    OVERWRITE_UNTRACKED="${OVERWRITE_UNTRACKED}${rel}"$'\n'
  fi
done < <(git -C "$CLONE" ls-tree -r --name-only "origin/${TARGET_BRANCH}")
if [ -n "$OVERWRITE_UNTRACKED" ]; then
  HOLD="${HOLD:-$HOLD_ROOT}"
  mkdir -p "$HOLD"
  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    dest="$HOLD/untracked/$rel"
    mkdir -p "$(dirname "$dest")"
    mv "$CLONE/$rel" "$dest"
    echo "OK: parked untracked-that-main-tracks: $rel -> $dest"
  done <<<"$OVERWRITE_UNTRACKED"
fi

if [ "$BEHIND" -eq 0 ] && [ "$AHEAD" -eq 0 ]; then
  echo "OK: already at origin/${TARGET_BRANCH} ($(git -C "$CLONE" rev-parse --short HEAD))"
else
  if ! git -C "$CLONE" reset --keep "origin/${TARGET_BRANCH}"; then
    echo "FAIL: git reset --keep aborted — a dirty tracked file would be overwritten." >&2
    echo "Work is still in the worktree. Unique commits: ${PRESERVE_BRANCH:-none}. Dirty park: ${DIRTY_REF:-none}. Hold: ${HOLD:-none}." >&2
    exit 1
  fi
fi

# Force origin blobs onto every colliding path and the rest of the tip.
# `reset --keep` plus an empty OVERWRITE list left CI with the local copy.
if [ "$BEHIND" -gt 0 ] || [ "$AHEAD" -gt 0 ] || [ -n "$OVERWRITE_UNTRACKED" ]; then
  git -C "$CLONE" checkout -f "origin/${TARGET_BRANCH}" -- .
fi

GITDIR_AFTER="$(git -C "$CLONE" rev-parse --git-common-dir)"
BRANCH_AFTER="$(git -C "$CLONE" rev-parse --abbrev-ref HEAD)"
if [ "$GITDIR_BEFORE" != "$GITDIR_AFTER" ] || [ "$BRANCH_BEFORE" != "$BRANCH_AFTER" ]; then
  echo "FAIL: gitdir or branch changed (swap or switch). This is not an in-place catch-up." >&2
  exit 2
fi

if [ -n "$VENV_BEFORE" ]; then
  if [ ! -e "$CLONE/.venv" ]; then
    echo "FAIL: .venv missing after catch-up — clone was clobbered." >&2
    exit 2
  fi
  VENV_AFTER="$(cd "$CLONE/.venv" && pwd -P)"
  if [ "$VENV_BEFORE" != "$VENV_AFTER" ]; then
    echo "FAIL: .venv path changed (${VENV_BEFORE} -> ${VENV_AFTER})." >&2
    exit 2
  fi
  echo "OK: .venv still at $CLONE/.venv"
fi

UNTRACKED_AFTER="$(git -C "$CLONE" ls-files --others --exclude-standard | LC_ALL=C sort)"
MISSING_UNTRACKED="$(comm -23 <(printf '%s\n' "$UNTRACKED_BEFORE") <(printf '%s\n' "$UNTRACKED_AFTER") | sed '/^$/d' || true)"
if [ -n "$MISSING_UNTRACKED" ]; then
  STILL_MISSING=""
  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    if git -C "$CLONE" ls-files --error-unmatch -- "$rel" >/dev/null 2>&1; then
      continue
    fi
    if [ -n "$HOLD" ] && [ -e "$HOLD/untracked/$rel" ]; then
      continue
    fi
    STILL_MISSING="${STILL_MISSING}${rel}"$'\n'
  done <<<"$MISSING_UNTRACKED"
  if [ -n "$STILL_MISSING" ]; then
    echo "FAIL: untracked paths disappeared and are not tracked or held:" >&2
    printf '%s' "$STILL_MISSING" >&2
    exit 2
  fi
fi

echo "OK: in-place catch-up ($CLONE @ $(git -C "$CLONE" rev-parse --short HEAD); was ${HEAD_BEFORE:0:12}; behind_was=${BEHIND} ahead_was=${AHEAD})"
if [ -n "$DIRTY_REF" ]; then
  echo "OK: dirty-tracked is recoverable: git stash apply ${DIRTY_REF}"
fi
if [ -n "$HOLD" ]; then
  echo "OK: parked copies are at ${HOLD}"
fi
exit 0
