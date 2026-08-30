#!/usr/bin/env bash
# Portable bounded-exec: GNU timeout, Homebrew gtimeout, or python3.
# Usage: run_with_timeout SECONDS command [args...]
# Exit 124 on expiry (GNU timeout compatible). Exit 127 if no runner exists.
# shellcheck shell=bash

run_with_timeout() {
  local secs="$1"
  shift
  if [ -z "${secs:-}" ] || [ "$#" -lt 1 ]; then
    echo "run_with_timeout: usage: run_with_timeout SECONDS command [args...]" >&2
    return 2
  fi
  case "$secs" in
    ''|*[!0-9.]*) echo "run_with_timeout: SECONDS must be numeric (got ${secs})" >&2; return 2 ;;
  esac
  if command -v timeout >/dev/null 2>&1; then
    timeout "$secs" "$@"
    return $?
  fi
  if command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$secs" "$@"
    return $?
  fi
  local py
  py="$(command -v python3 || true)"
  if [ -z "$py" ]; then
    echo "run_with_timeout: no timeout, gtimeout, or python3 on PATH" >&2
    return 127
  fi
  "$py" -c '
import subprocess
import sys

secs = float(sys.argv[1])
cmd = sys.argv[2:]
try:
    raise SystemExit(subprocess.run(cmd, timeout=secs).returncode)
except subprocess.TimeoutExpired:
    raise SystemExit(124)
except FileNotFoundError:
    raise SystemExit(127)
' "$secs" "$@"
}
