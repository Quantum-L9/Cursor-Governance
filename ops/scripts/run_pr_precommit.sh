#!/usr/bin/env bash
# Run repo-portable pre-commit hooks on changed files only (not --all-files).
# Full-tree: make precommit / nightly CI.
# sync-generated-artifacts is SKIPPED here — run_pr_gate heals with WARN+continue.
# On a local Cursor governance clone, do NOT skip symlinks-check (activation must
# be live). symlinks-check asserts Cursor desktop wiring (~/.cursor/plugins/local,
# .cursor-commands, .cursor/plans), so it only means something on the cursor
# surface — see the skip conditions below.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"
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
# symlinks-check asserts Cursor desktop activation. Skip it in CI, on a partial
# clone, and on any non-cursor surface: a headless adapter surface (claude-code,
# codex, …) can hold a FULL governance clone while having no Cursor install at
# all, so "full clone" alone does not imply "a Cursor machine". Without this the
# hook fails on wiring the surface is not supposed to have, and `make pr` — the
# only sanctioned route to GitHub — is unreachable there.
# PAIRED PREDICATE: run_pr_gate.sh skips consumer --workspace the same way.
# Isolates under $HOME/.l9 are git checkouts, not Cursor consumer workspaces.
if should_skip_consumer_symlink_checks "$WS"; then
  SKIP_LIST="${SKIP_LIST},symlinks-check"
fi
SKIP="$SKIP_LIST" pre-commit run --files "${files[@]}"
