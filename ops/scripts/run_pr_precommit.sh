#!/usr/bin/env bash
# Run repo-portable pre-commit hooks on changed files only (not --all-files).
# Full-tree: make precommit / nightly CI.
#
# .pre-commit-config.yaml is authoritative for every hook it declares, including
# ruff, ruff-format, and sync-generated-artifacts. The outer make pr gate must
# not re-execute those hooks.
#
# On a local Cursor governance clone, do NOT skip symlinks-check (activation must
# be live). symlinks-check asserts Cursor desktop wiring (~/.cursor/plugins/local,
# .cursor-commands, .cursor/plans), so it only means something on the cursor
# surface — see the skip conditions below.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/pr_gate_trace.sh
. "$SCRIPT_DIR/lib/pr_gate_trace.sh"
pr_gate_trace "precommit"

WS="${1:-${WS:-$(pwd)}}"
WS="$(cd "$WS" && pwd)"
PR_BASE="${PR_BASE:-}"
CHANGED_FILE="${L9_PR_CHANGED_FILE:-}"

command -v pre-commit >/dev/null 2>&1 || {
  echo "pre-commit not installed. Run: pip install pre-commit && pre-commit install" >&2
  exit 1
}

if [[ -z "$CHANGED_FILE" || ! -f "$CHANGED_FILE" ]]; then
  CHANGED_FILE="$(mktemp)"
  trap 'rm -f "$CHANGED_FILE"' EXIT
  PR_BASE="$PR_BASE" WS="$WS" bash "$SCRIPT_DIR/resolve_changed_files.sh" \
    >"$CHANGED_FILE" 2> >(grep -E '^(SOURCE:|ERROR:)' >&2 || true)
fi

if [[ ! -s "$CHANGED_FILE" ]]; then
  echo "OK: no changed files for pre-commit"
  exit 0
fi

files=()
while IFS= read -r f; do
  [[ -n "$f" ]] && files+=("$f")
done <"$CHANGED_FILE"
echo "pre-commit (changed files: ${#files[@]})"
cd "$WS"

# Only skip hooks that are not meaningful on this surface. Do not skip
# sync-generated-artifacts — pre-commit owns that hook.
SKIP_LIST=""
# symlinks-check asserts Cursor desktop activation. Skip it in CI, on a partial
# clone, and on any non-cursor surface: a headless adapter surface (claude-code,
# codex, …) can hold a FULL governance clone while having no Cursor install at
# all, so "full clone" alone does not imply "a Cursor machine". Without this the
# hook fails on wiring the surface is not supposed to have, and `make pr` — the
# only sanctioned route to GitHub — is unreachable there.
# PAIRED PREDICATE: run_pr_gate.sh gates check_governance_wiring.sh on the same
# surface test. Both assert Cursor desktop wiring; change them together.
SURFACE="${L9_GOVERNANCE_SURFACE:-}"
if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" \
   || ! -f "$WS/skills/AUTONOMY_MANIFEST.yaml" || ! -f "$WS/rules/RULES-MANIFEST.yaml" \
   || ( -n "$SURFACE" && "$SURFACE" != "cursor" ) ]]; then
  SKIP_LIST="symlinks-check"
fi
if [[ -n "$SKIP_LIST" ]]; then
  SKIP="$SKIP_LIST" pre-commit run --files "${files[@]}"
else
  pre-commit run --files "${files[@]}"
fi
