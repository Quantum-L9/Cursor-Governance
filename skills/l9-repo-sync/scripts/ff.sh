#!/usr/bin/env bash
# In-place catch-up for a named Cursor-Governance clone.
# Never deletes unique bytes. Step 0: if HEAD is not main, park dirt then
# `git switch` to main (feature ref stays). Then park unique main commits,
# dirty tracked, and untracked copies that origin now tracks. Then
# `git reset --keep`. Never stash -u. Never activate_fresh. Never reset
# --hard as the catch-up. Never reset a feature branch onto origin/main.
set -euo pipefail

# Inherit no host git dir — `git -C` is ignored when GIT_DIR is set.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_COMMON_DIR GIT_PREFIX

CLONE="${CURSOR_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
CLONE="$(cd "$CLONE" && pwd)"
_FF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
_SSOT_KEEP_LIB=""
for _ssot_keep_cand in \
  "${_FF_ROOT}/ops/scripts/lib/ssot_machine_local_keep.sh" \
  "${CLONE}/ops/scripts/lib/ssot_machine_local_keep.sh" \
  "$HOME/.cursor-governance/ops/scripts/lib/ssot_machine_local_keep.sh"; do
  if [ -f "$_ssot_keep_cand" ]; then
    _SSOT_KEEP_LIB="$_ssot_keep_cand"
    break
  fi
done
if [ -n "$_SSOT_KEEP_LIB" ]; then
  # shellcheck source=../../../ops/scripts/lib/ssot_machine_local_keep.sh
  . "$_SSOT_KEEP_LIB"
else
  ssot_is_machine_local_keep() {
    case "${1#./}" in
      .venv|.venv/*|.env.local|env.local|.claude/settings.local.json|.env.*.local) return 0 ;;
    esac
    return 1
  }
fi
unset _ssot_keep_cand
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

VENV_BEFORE=""
if [ -e "$CLONE/.venv" ]; then
  VENV_BEFORE="$(cd "$CLONE/.venv" && pwd -P)"
fi

KEEP_BEFORE=""
for _keep_rel in .venv .env.local env.local .claude/settings.local.json; do
  if [ -e "$CLONE/$_keep_rel" ] || [ -L "$CLONE/$_keep_rel" ]; then
    KEEP_BEFORE="${KEEP_BEFORE}${_keep_rel}"$'\n'
  fi
done
for _keep_f in "$CLONE"/.env.*.local; do
  [ -e "$_keep_f" ] || continue
  KEEP_BEFORE="${KEEP_BEFORE}$(basename "$_keep_f")"$'\n'
done
unset _keep_rel _keep_f

UNTRACKED_BEFORE="$(git -C "$CLONE" ls-files --others --exclude-standard | LC_ALL=C sort)"

echo "ff: clone=$CLONE branch=$BRANCH_BEFORE push=0 hard_reset=0 stash_u=0"
echo "ff: keeping .venv, env.local files, and untracked; unique commits and dirty tracked get preserve refs"

# A bare `fetch origin main` can leave origin/main stale (FETCH_HEAD only)
# on some CI git/refspec layouts; then behind=0 and colliding untracked
# files are never overwritten.
git -C "$CLONE" fetch --quiet origin \
  "+refs/heads/${TARGET_BRANCH}:refs/remotes/origin/${TARGET_BRANCH}"
if ! git -C "$CLONE" rev-parse --verify "origin/$TARGET_BRANCH" >/dev/null 2>&1; then
  echo "FAIL: origin/${TARGET_BRANCH} missing after fetch." >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PRESERVE_BRANCH=""
DIRTY_REF=""
HOLD=""
OVERWRITE_UNTRACKED=""
PARKED_UNTRACKED=0
CLONE_KEY="$(printf '%s' "$CLONE" | shasum -a 256 | awk '{print substr($1,1,12)}')"
HOLD_ROOT="${HOME}/.cursor/l9-ff-hold/${CLONE_KEY}/${STAMP}"

if [ -n "$KEEP_BEFORE" ]; then
  mkdir -p "$HOLD_ROOT/machine-local"
  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    [ "$rel" = ".venv" ] && continue
    dest="$HOLD_ROOT/machine-local/$rel"
    mkdir -p "$(dirname "$dest")"
    cp -a "$CLONE/$rel" "$dest"
  done <<<"$KEEP_BEFORE"
fi

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

# mode=always: park even at tip (required before switching off a feature branch).
# mode=maybe_leave: leave unique dirt in the worktree when already on origin/main.
_park_dirty_tracked() {
  local mode="$1"
  local DIRTY_TRACKED
  DIRTY_TRACKED="$(git -C "$CLONE" diff --name-only HEAD | LC_ALL=C sort | sed '/^$/d' || true)"
  [ -n "$DIRTY_TRACKED" ] || return 0
  if [ "$mode" = "maybe_leave" ] && [ "${BEHIND:-1}" -eq 0 ] && [ "${AHEAD:-1}" -eq 0 ]; then
    echo "OK: already at origin/${TARGET_BRANCH}; leaving unique dirty tracked in the worktree"
    echo "$DIRTY_TRACKED" | while IFS= read -r rel; do
      [ -z "$rel" ] && continue
      echo "ff: classify path=${rel} class=leave_at_tip"
    done
    return 0
  fi
  mkdir -p "$HOLD_ROOT/tracked"
  HOLD="$HOLD_ROOT"
  local DIRTY_SHA
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
}

_park_overwrite_untracked() {
  local found=""
  local rel dest
  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    if git -C "$CLONE" ls-files --error-unmatch -- "$rel" >/dev/null 2>&1; then
      continue
    fi
    if [ -e "$CLONE/$rel" ] || [ -L "$CLONE/$rel" ]; then
      found="${found}${rel}"$'\n'
    fi
  done < <(git -C "$CLONE" ls-tree -r --name-only "origin/${TARGET_BRANCH}")
  OVERWRITE_UNTRACKED="$found"
  [ -n "$OVERWRITE_UNTRACKED" ] || return 0
  PARKED_UNTRACKED=1
  HOLD="${HOLD:-$HOLD_ROOT}"
  mkdir -p "$HOLD"
  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    dest="$HOLD/untracked/$rel"
    mkdir -p "$(dirname "$dest")"
    mv "$CLONE/$rel" "$dest"
    echo "OK: parked untracked-that-main-tracks: $rel -> $dest"
  done <<<"$OVERWRITE_UNTRACKED"
}

_switch_to_target() {
  if git -C "$CLONE" show-ref --verify --quiet "refs/heads/${TARGET_BRANCH}"; then
    if ! git -C "$CLONE" switch --quiet "$TARGET_BRANCH"; then
      echo "FAIL: git switch ${TARGET_BRANCH} aborted after parking dirt." >&2
      echo "Feature ref ${BRANCH_BEFORE} is unchanged. Dirty park: ${DIRTY_REF:-none}. Hold: ${HOLD:-none}." >&2
      exit 1
    fi
  else
    if ! git -C "$CLONE" switch --quiet -c "$TARGET_BRANCH" --track "origin/${TARGET_BRANCH}"; then
      echo "FAIL: could not create local ${TARGET_BRANCH} tracking origin/${TARGET_BRANCH}." >&2
      echo "Feature ref ${BRANCH_BEFORE} is unchanged. Dirty park: ${DIRTY_REF:-none}. Hold: ${HOLD:-none}." >&2
      exit 1
    fi
  fi
  echo "OK: step 0 switched ${BRANCH_BEFORE} -> ${TARGET_BRANCH} (ref ${BRANCH_BEFORE} unchanged)"
}

if [ "$BRANCH_BEFORE" != "$TARGET_BRANCH" ]; then
  echo "ff: step 0 — park then switch to ${TARGET_BRANCH} (do not reset ${BRANCH_BEFORE})"
  _park_dirty_tracked always
  _park_overwrite_untracked
  _switch_to_target
fi

AHEAD="$(git -C "$CLONE" rev-list --count "origin/${TARGET_BRANCH}..HEAD")"
BEHIND="$(git -C "$CLONE" rev-list --count "HEAD..origin/${TARGET_BRANCH}")"

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
# non-overlapping dirt. leave_at_tip only applies when already on main.
_park_dirty_tracked maybe_leave

# origin/main may now track a path that is still untracked here. reset --keep
# may leave that worktree copy untouched. Walk origin's tree — do not depend
# on `comm` + `ls-files --others` (untracked-cache / excludesfile miss paths
# on some CI images).
_park_overwrite_untracked

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
if [ "$BEHIND" -gt 0 ] || [ "$AHEAD" -gt 0 ] || [ -n "$OVERWRITE_UNTRACKED" ] || [ "$PARKED_UNTRACKED" -eq 1 ]; then
  git -C "$CLONE" checkout -f "origin/${TARGET_BRANCH}" -- .
fi


if [ -d "$HOLD_ROOT/machine-local" ] && [ -n "$KEEP_BEFORE" ]; then
  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    [ "$rel" = ".venv" ] && continue
    src="$HOLD_ROOT/machine-local/$rel"
    [ -e "$src" ] || [ -L "$src" ] || continue
    mkdir -p "$(dirname "$CLONE/$rel")"
    cp -a "$src" "$CLONE/$rel"
    chmod go-rwx "$CLONE/$rel" 2>/dev/null || true
    echo "OK: restored machine-local $rel after catch-up"
  done <<<"$KEEP_BEFORE"
fi

GITDIR_AFTER="$(git -C "$CLONE" rev-parse --git-common-dir)"
BRANCH_AFTER="$(git -C "$CLONE" rev-parse --abbrev-ref HEAD)"
if [ "$GITDIR_BEFORE" != "$GITDIR_AFTER" ]; then
  echo "FAIL: gitdir changed (swap). This is not an in-place catch-up." >&2
  exit 2
fi
if [ "$BRANCH_AFTER" != "$TARGET_BRANCH" ]; then
  echo "FAIL: expected HEAD on ${TARGET_BRANCH} after catch-up, got ${BRANCH_AFTER}." >&2
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

if [ -n "$KEEP_BEFORE" ]; then
  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    if [ ! -e "$CLONE/$rel" ] && [ ! -L "$CLONE/$rel" ]; then
      echo "FAIL: machine-local keep path missing after catch-up: $rel" >&2
      exit 2
    fi
    echo "OK: kept $rel"
  done <<<"$KEEP_BEFORE"
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
