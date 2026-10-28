#!/usr/bin/env bash
# Shell reader of the governance venv readiness contract.
# shellcheck shell=bash
#
# Writer: ops/scripts/ensure_uv_environment.sh holds .l9/uv-environment.lock
# EXCLUSIVE for a whole install and leaves .l9/uv-environment.installing behind
# only if the install died or could not be verified. Python reader:
# ops/memory/venv_ready.py. This is the same contract for launchers that exec
# the venv's interpreter directly (the memory MCP server, python hooks), which
# Claude Code starts in parallel with the SessionStart hook that installs it.
#
# The lock authority is that one file. util-linux flock(1) waits on it when
# that binary is real util-linux. Every other host, including macOS, waits on
# the same fcntl.flock through ops/scripts/uv_environment_lock.py. A missing
# or failed probe is not readiness.
#
# Usage:
#   . ops/scripts/lib/venv_ready.sh
#   venv_ready_wait <governance-root> [seconds]
#   venv_ready_exec <governance-root> <interpreter> <script> [seconds]
# venv_ready_wait returns 0 ready, 1 still installing after the wait,
# 2 an interrupted install, 3 the lock could not be probed.
# venv_ready_exec replaces this process only when that result is ready.
# It returns the same non-zero codes when the interpreter must not run,
# and exits with the interpreter's status when it did run.
# Neither function creates files: a hot path must not write. Messages go to stderr.

_VENV_READY_LOCK_PY="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/uv_environment_lock.py"

_venv_ready_util_linux_flock() {
  command -v flock >/dev/null 2>&1 && flock --version 2>&1 | grep -q 'util-linux'
}

_venv_ready_interrupted() {
  local root="$1" marker="$2"
  echo "venv_ready: governance venv install was interrupted ($marker present); repair: bash $root/ops/scripts/ensure_uv_environment.sh $root apply" >&2
}

_venv_ready_busy() {
  local wait="$1" lock="$2"
  echo "venv_ready: governance venv install still in progress after ${wait}s ($lock held)" >&2
}

_venv_ready_probe_failed() {
  echo "venv_ready: lock probe failed (rc=$1); refusing to treat the venv as ready" >&2
}

_venv_ready_wait_posix() {
  local lock="$1" marker="$2" wait="$3" root="$4"
  local rc=0
  if ! command -v python3 >/dev/null 2>&1 || [ ! -f "$_VENV_READY_LOCK_PY" ]; then
    _venv_ready_probe_failed "unavailable"
    return 3
  fi
  python3 "$_VENV_READY_LOCK_PY" wait-shared \
    --lock "$lock" --wait "$wait" --marker "$marker" >/dev/null 2>&1 || rc=$?
  case "$rc" in
    0) return 0 ;;
    1) _venv_ready_busy "$wait" "$lock"; return 1 ;;
    2) _venv_ready_interrupted "$root" "$marker"; return 2 ;;
    *) _venv_ready_probe_failed "$rc"; return 3 ;;
  esac
}

venv_ready_wait() {
  local root="$1" wait="${2:-${L9_VENV_READY_WAIT_S:-15}}"
  local lock="$root/.l9/uv-environment.lock" marker="$root/.l9/uv-environment.installing"
  case "$wait" in ''|*[!0-9]*) wait=15 ;; esac
  if [ ! -e "$lock" ]; then
    if [ -e "$marker" ]; then
      _venv_ready_interrupted "$root" "$marker"
      return 2
    fi
    return 0
  fi
  if _venv_ready_util_linux_flock; then
    if ! flock -s -w "$wait" "$lock" true 2>/dev/null; then
      _venv_ready_busy "$wait" "$lock"
      return 1
    fi
    if [ -e "$marker" ]; then
      _venv_ready_interrupted "$root" "$marker"
      return 2
    fi
    return 0
  fi
  _venv_ready_wait_posix "$lock" "$marker" "$wait" "$root"
}

# Non-blocking recheck for a caller that must not hold the lock across a
# long-lived process. Same codes as venv_ready_wait. A live writer is busy,
# never ready and never interrupted.
venv_ready_confirm() {
  local root="$1"
  local lock="$root/.l9/uv-environment.lock" marker="$root/.l9/uv-environment.installing"
  local rc=0
  if [ ! -e "$lock" ]; then
    if [ -e "$marker" ]; then
      _venv_ready_interrupted "$root" "$marker"
      return 2
    fi
    return 0
  fi
  if _venv_ready_util_linux_flock; then
    if ! flock -s -n "$lock" true 2>/dev/null; then
      _venv_ready_busy "0" "$lock"
      return 1
    fi
    if [ -e "$marker" ]; then
      _venv_ready_interrupted "$root" "$marker"
      return 2
    fi
    return 0
  fi
  if ! command -v python3 >/dev/null 2>&1 || [ ! -f "$_VENV_READY_LOCK_PY" ]; then
    _venv_ready_probe_failed "unavailable"
    return 3
  fi
  python3 "$_VENV_READY_LOCK_PY" wait-shared \
    --lock "$lock" --wait 0 --marker "$marker" >/dev/null 2>&1 || rc=$?
  case "$rc" in
    0) return 0 ;;
    1) _venv_ready_busy "0" "$lock"; return 1 ;;
    2) _venv_ready_interrupted "$root" "$marker"; return 2 ;;
    *) _venv_ready_probe_failed "$rc"; return 3 ;;
  esac
}

venv_ready_exec() {
  local root="$1" py="$2" script="$3" wait="${4:-${L9_VENV_READY_WAIT_S:-15}}"
  local lock="$root/.l9/uv-environment.lock" marker="$root/.l9/uv-environment.installing"
  local rc=0
  case "$wait" in ''|*[!0-9]*) wait=15 ;; esac
  if [ ! -e "$lock" ]; then
    if [ -e "$marker" ]; then
      _venv_ready_interrupted "$root" "$marker"
      return 2
    fi
    # Success replaces this process. Failure falls through and is not readiness.
    # shellcheck disable=SC2093
    exec "$py" "$script"
    _venv_ready_probe_failed "exec"
    return 3
  fi
  # One process holds the shared lock and replaces itself with the interpreter.
  # A separate wait-then-exec would let a writer replace .venv in the gap.
  if ! command -v python3 >/dev/null 2>&1 || [ ! -f "$_VENV_READY_LOCK_PY" ]; then
    _venv_ready_probe_failed "unavailable"
    return 3
  fi
  python3 "$_VENV_READY_LOCK_PY" exec-shared \
    --lock "$lock" --wait "$wait" --marker "$marker" -- "$py" "$script" || rc=$?
  # 80/81/82: the helper did not execute the interpreter.
  # Any other status is the interpreter's own exit.
  case "$rc" in
    80) _venv_ready_busy "$wait" "$lock"; return 1 ;;
    81) _venv_ready_interrupted "$root" "$marker"; return 2 ;;
    82) _venv_ready_probe_failed "$rc"; return 3 ;;
    *) exit "$rc" ;;
  esac
}
