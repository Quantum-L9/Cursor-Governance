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
# Usage:
#   . ops/scripts/lib/venv_ready.sh
#   venv_ready_wait <governance-root> [seconds]
# Returns 0 ready (or no lock/flock to honour), 1 still installing after the
# wait, 2 an interrupted install. Never creates files: a hot path (every
# PreToolUse hook) must not write. Messages go to stderr.

venv_ready_wait() {
  local root="$1" wait="${2:-${L9_VENV_READY_WAIT_S:-15}}"
  local lock="$root/.l9/uv-environment.lock" marker="$root/.l9/uv-environment.installing"
  case "$wait" in ''|*[!0-9]*) wait=15 ;; esac
  if [ -e "$lock" ] && command -v flock >/dev/null 2>&1; then
    if ! flock -s -w "$wait" "$lock" true 2>/dev/null; then
      echo "venv_ready: governance venv install still in progress after ${wait}s ($lock held)" >&2
      return 1
    fi
  fi
  if [ -e "$marker" ]; then
    echo "venv_ready: governance venv install was interrupted ($marker present); repair: bash $root/ops/scripts/ensure_uv_environment.sh $root apply" >&2
    return 2
  fi
  return 0
}
