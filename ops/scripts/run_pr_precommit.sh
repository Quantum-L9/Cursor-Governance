#!/usr/bin/env bash
# INTERNAL leaf of `make pr-check` / `run_pr_gate.sh`.
# Runs the hook catalog in .pre-commit-config.yaml on changed files only.
# This is not a public gate and not a git commit hook. Full-tree of the same
# catalog is INTERNAL `make precommit` (nightly / make pr-full).
# sync-generated-artifacts is SKIPPED here — run_pr_gate heals with WARN+continue.
# On a local Cursor governance clone, do NOT skip symlinks-check (activation must
# be live). symlinks-check asserts Cursor desktop wiring (~/.cursor/plugins/local,
# .cursor-commands, .cursor/plans), so it only means something on the cursor
# surface — see the skip conditions below.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"
# Staged mode: invoked from a git commit hook rather than from make pr-check.
# Same catalog, same SKIP list — the single reason `pre-commit install` is
# forbidden is that a RAW shim runs the catalog WITHOUT that list, so
# symlinks-check rejects every commit on a non-cursor surface. Delegating here
# keeps the list, which is what makes a commit hook safe on every surface.
PR_STAGED="${PR_STAGED:-0}"
if [[ "${1:-}" == "--staged" ]]; then
  PR_STAGED=1
  shift
fi

WS="${1:-${WS:-$(pwd)}}"
WS="$(cd "$WS" && pwd)"
PR_BASE="${PR_BASE:-}"

# CI-008 governance-always: the publish gate runs the GOVERNANCE pre-commit
# config as its authority, named explicitly rather than picked up from the
# workspace cwd. Resolve the governance clone root now (this script lives in
# $GOV/ops/scripts) and pass it as `--config` below. When the workspace IS the
# governance clone (WS == GOV_ROOT) the named config is byte-identical to the
# cwd config, so this is a strict no-op and the governance repo's own `make pr`
# is unchanged.
#
# NOTE (scoped follow-up): running this governance config against a *consumer*
# workspace (WS != GOV_ROOT) additionally needs cwd=$GOV_ROOT so the config's
# repo-local `entry: ops/scripts/...` hooks resolve, absolute --files paths, and
# a governance-only-local-hook skip subset. That path requires validation
# against a real consumer checkout (not available in this environment), so it is
# not enabled here; the explicit config binding is the safe, in-repo-validated
# half of §8b.
GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GOV_PRECOMMIT_CONFIG="$GOV_ROOT/.pre-commit-config.yaml"

# Resolve first. An empty list is PASS without the pre-commit CLI — CI Test
# Suite does not install it, and this repo does not use a git commit hook.
if [[ "$PR_STAGED" == "1" ]]; then
  tmp="$(mktemp)"
  trap 'rm -f "$tmp"' EXIT
  git -C "$WS" diff --cached --name-only --diff-filter=ACMR >"$tmp"
elif [[ -n "${PR_CHANGED_FILE:-}" && -f "$PR_CHANGED_FILE" ]]; then
  tmp="$PR_CHANGED_FILE"
else
  tmp="$(mktemp)"
  trap 'rm -f "$tmp"' EXIT
  PR_BASE="$PR_BASE" WS="$WS" bash "$SCRIPT_DIR/resolve_changed_files.sh" \
    >"$tmp" 2> >(grep -E '^(SOURCE:|ERROR:)' >&2 || true)
fi

if [[ ! -s "$tmp" ]]; then
  echo "OK: no changed files for pre-commit"
  exit 0
fi

command -v pre-commit >/dev/null 2>&1 || {
  echo "FAIL: pre-commit CLI missing (INTERNAL leaf of make pr-check)." >&2
  echo "      Install the framework: pipx install pre-commit" >&2
  echo "      Do not run 'pre-commit install' — this repo has no git commit hook." >&2
  echo "      Public quality gate: make pr-check" >&2
  exit 1
}

files=()
while IFS= read -r f; do
  [[ -n "$f" ]] && files+=("$f")
done <"$tmp"
echo "pre-commit (changed files: ${#files[@]})"
if [[ ${#files[@]} -eq 0 ]]; then
  echo "OK: no in-scope files for pre-commit (scratch-only or empty after filter)"
  exit 0
fi
cd "$WS"

# Always skip sync in make pr path (heal happens in run_pr_gate).
# Corpus hooks (hygiene, residue, rules/skills ratchet) belong to
# make precommit / make pr-full, not the velocity path.
SKIP_LIST="sync-generated-artifacts,repo-hygiene,legacy-doctrine-residue,rules-check,skills-check"
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

# Hooks may rewrite (ruff --fix, format, eof, trailing-ws). Do not exit on
# pre-commit's files_modified status until dirt is classified below.
set +e
SKIP="$SKIP_LIST" pre-commit run --config "$GOV_PRECOMMIT_CONFIG" --files "${files[@]}"
pc_rc=$?
set -e

echo "--- lint-ruff (changed Python) ---"
py_list="$(mktemp)"
# Never delete a caller-owned PR_CHANGED_FILE. Only unlink temps we created.
if [[ -n "${PR_CHANGED_FILE:-}" && "$tmp" == "$PR_CHANGED_FILE" ]]; then
  trap 'rm -f "$py_list"' EXIT
else
  trap 'rm -f "$tmp" "$py_list"' EXIT
fi
grep -E '\.(py|pyi)$' "$tmp" >"$py_list" || true
if [[ ! -s "$py_list" ]]; then
  echo "OK: no changed Python files for ruff"
else
  echo "ruff (changed): $(grep -c . "$py_list") file(s)"
  _ruff="$GOV_ROOT/.venv/bin/ruff"
  if [[ ! -x "$_ruff" && -n "${GOV_TOOLCHAIN_ROOT:-}" && -x "$GOV_TOOLCHAIN_ROOT/.venv/bin/ruff" ]]; then
    _ruff="$GOV_TOOLCHAIN_ROOT/.venv/bin/ruff"
  fi
  if [[ ! -x "$_ruff" ]]; then
    echo "FAIL: locked ruff missing at $GOV_ROOT/.venv/bin/ruff (run: make venv)" >&2
    exit 1
  fi
  xargs "$_ruff" check <"$py_list"
  xargs "$_ruff" format --check <"$py_list"
fi

# Fail closed on tracked dirt. Do not auto-stage — commit the rewrite, re-run.
#
# Skipped in staged mode, and it must be: during a commit hook the staged
# changes themselves are tracked dirt, so this assertion can never hold and
# would reject every commit. A hook rewrite is still caught — pre-commit
# reports files_modified and $pc_rc is non-zero below.
if [[ "$PR_STAGED" != "1" ]] && git status --porcelain | grep -qvE '^\?\?'; then
  echo "FAIL: tracked files dirty after precommit-repo — commit the rewrite, then re-run."
  echo "      Do not auto-stage. Paths:"
  git status --porcelain | grep -vE '^\?\?'
  exit 1
fi

if [[ "$pc_rc" -ne 0 ]]; then
  echo "FAIL: pre-commit exited ${pc_rc}" >&2
  exit "$pc_rc"
fi

if [[ "$PR_STAGED" == "1" ]]; then
  echo "OK: staged changes pass the governance hook catalog"
else
  echo "OK: precommit-repo clean (hooks + lint-ruff, no tracked dirt)"
fi
