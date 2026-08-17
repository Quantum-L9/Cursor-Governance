#!/usr/bin/env bash
# Idempotent local registration of the l9-generated merge driver. git config is
# per-clone and untracked, so check_governance_wiring.sh calls this every
# session to self-heal registration. Exit 0 = driver registered (+ verified).
#
# Usage: ensure_git_merge_drivers.sh [repo-path] [--check-attributes]
#   --check-attributes also reports whether .gitattributes declares
#   merge=l9-generated (governance clones only — consumer repos legitimately
#   have no generated-artifact attributes).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DRIVER="$SCRIPT_DIR/git_merge_driver_generated.sh"
CHECK_ATTRIBUTES=0
REPO="$(pwd)"

for arg in "$@"; do
  case "$arg" in
    --check-attributes) CHECK_ATTRIBUTES=1 ;;
    -*) echo "unknown flag: $arg" >&2; exit 2 ;;
    *) REPO="$arg" ;;
  esac
done

REPO="$(cd "$REPO" 2>/dev/null && pwd)" || { echo "no such dir: $REPO" >&2; exit 1; }
if ! git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1; then
  echo "skip: not a git repo: $REPO"
  exit 0
fi

if [ ! -f "$DRIVER" ]; then
  echo "FAIL: merge driver script missing: $DRIVER" >&2
  exit 1
fi

git -C "$REPO" config merge.l9-generated.name "l9 generated artifacts — keep ours, regenerate after merge"
git -C "$REPO" config merge.l9-generated.driver "bash \"$DRIVER\" %O %A %B %P"

driver="$(git -C "$REPO" config --get merge.l9-generated.driver || true)"
if [ -z "$driver" ]; then
  echo "FAIL: merge.l9-generated.driver not registered in $REPO" >&2
  exit 1
fi
echo "OK: merge.l9-generated.driver = $driver"

if [ "$CHECK_ATTRIBUTES" -eq 1 ]; then
  if [ -f "$REPO/.gitattributes" ] && grep -q "merge=l9-generated" "$REPO/.gitattributes"; then
    echo "OK: .gitattributes declares merge=l9-generated"
  else
    echo "WARN: no merge=l9-generated entries in .gitattributes (text-merge fallback for generated paths)"
  fi
fi

exit 0
