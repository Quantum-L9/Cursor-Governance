#!/usr/bin/env bash
# Run repo-portable pre-commit hooks on changed files only (not --all-files).
# Full-tree: make precommit / nightly CI.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WS="${1:-${WS:-$(pwd)}}"
WS="$(cd "$WS" && pwd)"
PR_BASE="${PR_BASE:-}"

command -v pre-commit >/dev/null 2>&1 || {
  echo "pre-commit not installed. Run: pip install pre-commit && pre-commit install" >&2
  exit 1
}

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
PR_BASE="$PR_BASE" WS="$WS" bash "$SCRIPT_DIR/resolve_changed_files.sh" \
  >"$tmp" 2> >(grep -E '^(SOURCE:|ERROR:)' >&2 || true)

if [[ ! -s "$tmp" ]]; then
  echo "OK: no changed files for pre-commit"
  exit 0
fi

count="$(grep -c . "$tmp" || true)"
echo "pre-commit (changed files: ${count})"
cd "$WS"
# shellcheck disable=SC2046
SKIP=symlinks-check pre-commit run --files $(cat "$tmp")
