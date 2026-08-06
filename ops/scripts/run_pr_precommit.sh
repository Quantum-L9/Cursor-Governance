#!/usr/bin/env bash
# Run repo-portable pre-commit hooks on changed files only (not --all-files).
# Full-tree: make precommit / nightly CI.
# sync-generated-artifacts is SKIPPED here — run_pr_gate heals with WARN+continue.
# On a local governance clone, do NOT skip symlinks-check (activation must be live).
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

files=()
while IFS= read -r f; do
  [[ -n "$f" ]] && files+=("$f")
done <"$tmp"
echo "pre-commit (changed files: ${#files[@]})"
cd "$WS"

# Always skip sync in make pr path (heal happens in run_pr_gate).
SKIP_LIST="sync-generated-artifacts"
if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" || ! -f "$WS/skills/AUTONOMY_MANIFEST.yaml" || ! -f "$WS/rules/RULES-MANIFEST.yaml" ]]; then
  SKIP_LIST="${SKIP_LIST},symlinks-check"
fi
SKIP="$SKIP_LIST" pre-commit run --files "${files[@]}"
