#!/usr/bin/env bash
# Repo-write lock: serializes *automated* writers against one workspace.
# shellcheck shell=bash
#
# Why this exists: pre-commit decides "files were modified by this hook" by
# diffing the tracked worktree around each hook (pre_commit/commands/run.py
# _run_single_hook). Any writer active during that window is blamed on the hook
# that happened to be running. Backgrounded sessionStart reconcilers
# (install_ide_profile.sh, setup_claude_code_plugins.sh) are exactly such
# writers, so `make pr` holds this lock and they yield to it.
#
# Boundaries:
#   - machine-local and short-lived. The tracked `.governance-build-lock` file
#     is an independent long-lived human kill switch; do not conflate them.
#   - serializes automation only. Parallel humans/agents on one clone remain
#     governed by rules/49-shared-worktree-isolation.mdc (use a worktree).
#   - fail-soft: an unusable lock never blocks the caller.
#
# Usage:
#   source ops/scripts/lib/repo_write_lock.sh
#   if repo_write_lock_acquire "$WS" 20; then ... ; repo_write_lock_release; fi
#   repo_write_lock_holder "$WS"     # ledger line for diagnostics, or empty
#
# Env:
#   L9_REPO_WRITE_LOCK=0        disable entirely (acquire always succeeds)
#   L9_REPO_WRITE_LOCK_OWNER    pid of the holder; set by the acquirer and
#                               inherited by children so nested governance
#                               scripts do not self-block
#   L9_REPO_WRITE_LOCK_STALE_S  stale-break age in seconds (default 300)
#   L9_REPO_WRITE_LOCK_LABEL    label recorded in the ledger (default $0 name)

REPO_WRITE_LOCK_STALE_S="${L9_REPO_WRITE_LOCK_STALE_S:-300}"

# Internal state for release. Only meaningful in the acquiring shell.
_REPO_WRITE_LOCK_DIR=""
_REPO_WRITE_LOCK_FD_OPEN=0

repo_write_lock_disabled() {
  case "${L9_REPO_WRITE_LOCK:-1}" in
    0 | false | no) return 0 ;;
    *) return 1 ;;
  esac
}

# Stable per-workspace lock id without invoking python (this runs on hot paths).
repo_write_lock_id() {
  local ws="${1:-$PWD}"
  printf '%s' "$ws" | cksum | awk '{print $1}'
}

repo_write_lock_dir() {
  local ws="${1:-$PWD}"
  printf '%s/.cursor/l9-repo-write.%s.lock.d' "$HOME" "$(repo_write_lock_id "$ws")"
}

# Ledger line: "<pid> <epoch> <workspace> <label>"
repo_write_lock_holder() {
  local dir
  dir="$(repo_write_lock_dir "${1:-$PWD}")"
  [ -f "$dir/owner" ] && cat "$dir/owner" 2>/dev/null
}

repo_write_lock_holder_pid() {
  repo_write_lock_holder "${1:-$PWD}" | awk '{print $1}'
}

# True when this process tree already owns the lock (re-entrancy).
repo_write_lock_held_by_me() {
  local ws="${1:-$PWD}" owner_pid
  [ -n "${L9_REPO_WRITE_LOCK_OWNER:-}" ] || return 1
  owner_pid="$(repo_write_lock_holder_pid "$ws")"
  [ -n "$owner_pid" ] && [ "$owner_pid" = "$L9_REPO_WRITE_LOCK_OWNER" ]
}

# Break a lock whose owner is gone or whose ledger is older than the stale age.
_repo_write_lock_break_if_stale() {
  local dir="$1" owner_pid ts now age
  owner_pid="$(awk '{print $1}' "$dir/owner" 2>/dev/null || echo "")"
  ts="$(awk '{print $2}' "$dir/owner" 2>/dev/null || echo 0)"
  now="$(date +%s 2>/dev/null || echo 0)"

  if [ -n "$owner_pid" ] && ! kill -0 "$owner_pid" 2>/dev/null; then
    rm -rf "$dir" 2>/dev/null || true
    return 0
  fi
  case "$ts" in '' | *[!0-9]*) ts=0 ;; esac
  case "$now" in '' | *[!0-9]*) now=0 ;; esac
  if [ "$now" -gt 0 ] && [ "$ts" -gt 0 ]; then
    age=$((now - ts))
    if [ "$age" -gt "$REPO_WRITE_LOCK_STALE_S" ]; then
      rm -rf "$dir" 2>/dev/null || true
      return 0
    fi
  fi
  return 1
}

_repo_write_lock_write_ledger() {
  local dir="$1" ws="$2"
  printf '%s %s %s %s\n' \
    "$$" "$(date +%s 2>/dev/null || echo 0)" "$ws" "${L9_REPO_WRITE_LOCK_LABEL:-${0##*/}}" \
    >"$dir/owner" 2>/dev/null || true
}

# repo_write_lock_acquire <workspace> [timeout_seconds]
# 0 = held (or lock disabled / already ours), 1 = not acquired within timeout.
repo_write_lock_acquire() {
  local ws="${1:-$PWD}" timeout="${2:-0}" dir waited=0

  if repo_write_lock_disabled; then
    return 0
  fi
  if repo_write_lock_held_by_me "$ws"; then
    return 0
  fi

  dir="$(repo_write_lock_dir "$ws")"
  mkdir -p "$(dirname "$dir")" 2>/dev/null || return 0 # unusable HOME: fail-soft

  while :; do
    if mkdir "$dir" 2>/dev/null; then
      _repo_write_lock_write_ledger "$dir" "$ws"
      _REPO_WRITE_LOCK_DIR="$dir"
      export L9_REPO_WRITE_LOCK_OWNER="$$"
      # Where available, also hold a kernel lock on a sidecar file so a
      # hard-killed holder is detectable without waiting out the stale age.
      if command -v flock >/dev/null 2>&1; then
        if exec 9>"$dir/owner.flock" 2>/dev/null && flock -n 9 2>/dev/null; then
          _REPO_WRITE_LOCK_FD_OPEN=1
        fi
      fi
      return 0
    fi

    _repo_write_lock_break_if_stale "$dir" && continue

    if [ "$waited" -ge "$timeout" ]; then
      return 1
    fi
    sleep 1
    waited=$((waited + 1))
  done
}

repo_write_lock_release() {
  if [ "$_REPO_WRITE_LOCK_FD_OPEN" = "1" ]; then
    exec 9>&- 2>/dev/null || true
    _REPO_WRITE_LOCK_FD_OPEN=0
  fi
  if [ -n "$_REPO_WRITE_LOCK_DIR" ]; then
    rm -rf "$_REPO_WRITE_LOCK_DIR" 2>/dev/null || true
    _REPO_WRITE_LOCK_DIR=""
    unset L9_REPO_WRITE_LOCK_OWNER
  fi
}

# Human-readable reason for a caller that decided to skip its work.
repo_write_lock_skip_note() {
  local ws="${1:-$PWD}" holder
  holder="$(repo_write_lock_holder "$ws")"
  if [ -n "$holder" ]; then
    printf 'repo-write lock held by %s' "$holder"
  else
    printf 'repo-write lock held by an unknown holder'
  fi
}
