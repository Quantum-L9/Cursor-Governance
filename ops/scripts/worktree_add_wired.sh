#!/usr/bin/env bash
# Sanctioned git worktree add + wire. Agents must use this instead of raw
# `git worktree add`. Inner git is not a Cursor beforeShellExecution command.
#
# Usage (from a git repo, same args as `git worktree add` after the subcommand):
#   bash ops/scripts/worktree_add_wired.sh -b feat/foo /path/to/wt origin/main
#   bash ops/scripts/worktree_add_wired.sh /path/to/wt
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export L9_WORKTREE_ADD_AUTHORIZED="${L9_WORKTREE_ADD_AUTHORIZED:-worktree_add_wired}"

if [ "$#" -lt 1 ]; then
  echo "usage: worktree_add_wired.sh <git worktree add args...>" >&2
  exit 2
fi

path=""
i=1
while [ "$i" -le "$#" ]; do
  eval "a=\${$i}"
  case "$a" in
    -b|-B|--reason)
      i=$((i + 2))
      ;;
    --lock)
      i=$((i + 1))
      ;;
    -*)
      i=$((i + 1))
      ;;
    *)
      path="$a"
      break
      ;;
  esac
done

if [ -z "$path" ]; then
  echo "ERROR: could not parse worktree path from: $*" >&2
  exit 2
fi

git worktree add "$@"
if [ ! -d "$path" ]; then
  echo "ERROR: worktree path missing after add: $path" >&2
  exit 1
fi

# Links only, like every other programmatic worktree creator. The full
# reconciler reaches install_ide_profile.sh -> agentdocs.sh, which writes the
# formatter block into a consumer's tracked AGENTS.md / CLAUDE.md, so a new
# worktree would start dirty in governed documents. Machine-wide setup already
# ran for the parent checkout; sessionStart and `make ide-profile` still
# reconcile the IDE profile deliberately.
L9_WIRE_LINKS_ONLY=1 bash "$SCRIPT_DIR/ensure_workspace_wired.sh" "$path"

# Every repo builds this tree's .venv with its own `make venv`.
# The recipe may live in an included fragment, so ask Make; do not grep
# the root Makefile and do not branch on uv.lock or requirements*.txt.
# make -q: 0 up to date, 1 would run, 2 no such target. A symlink to
# another checkout's .venv is not a substitute.
if ! command -v make >/dev/null 2>&1; then
  echo "ERROR: make is not on PATH; cannot build $path/.venv" >&2
  exit 1
fi
make_venv_rc=0
make -C "$path" -q venv >/dev/null 2>&1 || make_venv_rc=$?
if [ "$make_venv_rc" -eq 0 ] || [ "$make_venv_rc" -eq 1 ]; then
  echo "--- venv (make venv) ---"
  make -C "$path" venv
fi
