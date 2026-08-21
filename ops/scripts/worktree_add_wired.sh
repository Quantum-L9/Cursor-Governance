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

bash "$SCRIPT_DIR/ensure_workspace_wired.sh" "$path"

# Real locked venv in this tree. A symlink to another checkout's .venv fails
# ensure_gov_python.sh (sys.prefix != this path). Consumer repos without
# pyproject.toml + uv.lock are skipped.
if [ -f "$path/pyproject.toml" ] && [ -f "$path/uv.lock" ]; then
  echo "--- make venv (uv sync --locked --extra dev) ---"
  bash "$SCRIPT_DIR/ensure_gov_python.sh" "$path"
fi
