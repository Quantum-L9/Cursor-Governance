#!/usr/bin/env bash
# Idempotent local registration of the l9 merge drivers. git config is
# per-clone and untracked, so check_governance_wiring.sh calls this every
# session to self-heal registration. Exit 0 = drivers registered (+ verified).
#
#   merge.l9-generated  keep ours + regenerate (attributes: tracked .gitattributes)
#   merge.l9-versions   module version churn: __manifest__.py "version", README
#                       front-matter module_version:, tests/__init__.py imports
#                       (git_merge_driver_versions.py). Its attributes go to the
#                       clone's own $GIT_DIR/info/attributes, never to a tracked
#                       .gitattributes, so a consumer repository is not edited.
#
# Usage: ensure_git_merge_drivers.sh [repo-path] [--check-attributes]
#   --check-attributes also reports whether .gitattributes declares
#   merge=l9-generated (governance clones only — consumer repos legitimately
#   have no generated-artifact attributes).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DRIVER="$SCRIPT_DIR/git_merge_driver_generated.sh"
VERSIONS_DRIVER="$SCRIPT_DIR/git_merge_driver_versions.py"
CHECK_ATTRIBUTES=0
REPO="$(pwd)"

_is_ephemeral_path() {
  case "$1" in
    */.l9/gov-worktrees/*|*/.l9/program-worktrees/*|*/.l9/worktrees/*) return 0 ;;
    *) return 1 ;;
  esac
}

# Extracts share the clone gitdir. Registering an extract-absolute driver
# poisons merge-tree for every worktree after that extract is removed.
_canon_dir="${CURSOR_GOVERNANCE_DIR:-$HOME/.cursor-governance}/ops/scripts"
_canon="$_canon_dir/git_merge_driver_generated.sh"
_canon_versions="$_canon_dir/git_merge_driver_versions.py"
if _is_ephemeral_path "$SCRIPT_DIR" || _is_ephemeral_path "$DRIVER"; then
  if [ -f "$_canon" ]; then
    DRIVER="$_canon"
  fi
  if [ -f "$_canon_versions" ]; then
    VERSIONS_DRIVER="$_canon_versions"
  fi
fi

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

# --- l9-versions -----------------------------------------------------------
if [ ! -f "$VERSIONS_DRIVER" ]; then
  echo "FAIL: merge driver script missing: $VERSIONS_DRIVER" >&2
  exit 1
fi
git -C "$REPO" config merge.l9-versions.name "l9 module versions — bump above both sides, union test imports"
git -C "$REPO" config merge.l9-versions.driver "python3 \"$VERSIONS_DRIVER\" %O %A %B %P"
vdriver="$(git -C "$REPO" config --get merge.l9-versions.driver || true)"
if [ -z "$vdriver" ]; then
  echo "FAIL: merge.l9-versions.driver not registered in $REPO" >&2
  exit 1
fi
echo "OK: merge.l9-versions.driver = $vdriver"

# The attribute lines live in one managed block, rewritten whole on every run
# (idempotent; other lines in the file are kept). $GIT_DIR/info/attributes
# outranks every .gitattributes, so the block re-asserts the tracked
# merge=l9-generated lines after its own: a later line wins per attribute, and
# without this a generated README.md would lose keep-ours to l9-versions.
INFO_ATTR="$(git -C "$REPO" rev-parse --path-format=absolute --git-path info/attributes)"
mkdir -p "$(dirname "$INFO_ATTR")"
BEGIN_MARK="# BEGIN l9-versions (managed by ops/scripts/ensure_git_merge_drivers.sh)"
END_MARK="# END l9-versions"
block="$(
  printf '%s\n' "$BEGIN_MARK"
  printf '%s\n' "**/__manifest__.py merge=l9-versions"
  printf '%s\n' "**/README.md merge=l9-versions"
  printf '%s\n' "**/tests/__init__.py merge=l9-versions"
  if [ -f "$REPO/.gitattributes" ]; then
    grep -E '^[^#[:space:]][^[:space:]]*[[:space:]].*merge=l9-generated' "$REPO/.gitattributes" || true
  fi
  printf '%s\n' "$END_MARK"
)"
tmp_attr="$(mktemp "${INFO_ATTR}.XXXXXX")"
if [ -f "$INFO_ATTR" ]; then
  awk -v b="$BEGIN_MARK" -v e="$END_MARK" '
    $0 == b { skip = 1; next }
    $0 == e { skip = 0; next }
    !skip { print }
  ' "$INFO_ATTR" >"$tmp_attr"
fi
printf '%s\n' "$block" >>"$tmp_attr"
mv "$tmp_attr" "$INFO_ATTR"
echo "OK: l9-versions attributes in $INFO_ATTR"

if [ "$CHECK_ATTRIBUTES" -eq 1 ]; then
  if [ -f "$REPO/.gitattributes" ] && grep -q "merge=l9-generated" "$REPO/.gitattributes"; then
    echo "OK: .gitattributes declares merge=l9-generated"
  else
    echo "WARN: no merge=l9-generated entries in .gitattributes (text-merge fallback for generated paths)"
  fi
fi

exit 0
