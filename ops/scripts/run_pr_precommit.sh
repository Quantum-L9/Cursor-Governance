#!/usr/bin/env bash
# INTERNAL leaf of `make pr-check` / `run_pr_gate.sh`.
# Runs the hook catalog in .pre-commit-config.yaml on changed files only.
# This is not a public gate and not a git commit hook. Full-tree of the same
# catalog is INTERNAL `make precommit` (nightly / make pr-full).
#
# PR_PRECOMMIT_STAGE:
#   unset     — standalone make precommit-repo: kernel, writers, dirty-stop, readers
#   writers   — kernel + writer hooks + locked ruff --fix/format + dirty-stop
#   readers   — read-only hooks only (no kernel, no ruff)
# Each hook id runs at most once per invocation. Complementary SKIP lists.
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
STAGE="${PR_PRECOMMIT_STAGE:-}"
# shellcheck source=lib/fetch_receipt.sh
source "$SCRIPT_DIR/lib/fetch_receipt.sh"
# shellcheck source=lib/resolve_pr_stack.sh
source "$SCRIPT_DIR/lib/resolve_pr_stack.sh"

# Standalone make precommit-repo has no PR_CHANGED_FILE. Bind the unique chain
# tip before resolve_changed_files so kernel_gate does not see parent-stack
# fixtures. The gate already resolved and passes PR_CHANGED_FILE — skip.
if [[ -z "${PR_CHANGED_FILE:-}" || ! -f "${PR_CHANGED_FILE:-}" ]]; then
  PR_BASE="${PR_BASE:-origin/main}"
  pr_stack_apply_publish_base "$WS" || exit $?
  export PR_BASE
fi

# CI-008 governance-always: the publish gate runs the GOVERNANCE pre-commit
# config as its authority, named explicitly rather than picked up from the
# workspace cwd. Resolve the governance clone root now (this script lives in
# $GOV/ops/scripts) and pass it as `--config` below. When the workspace IS the
# governance clone (WS == GOV_ROOT) the named config is byte-identical to the
# cwd config, so this is a strict no-op and the governance repo's own `make pr`
# is unchanged.
#
# The governance-only-local-hook skip subset (_GOV_ONLY_SKIP below) is one half
# of the follow-up this note used to defer, now implemented: a hook whose
# `entry: ops/scripts/...` resolves against the WORKSPACE cannot run in a
# consumer checkout, where that script does not exist. Validated against a real
# consumer checkout (Quantum-L9/l9-repo-template), where the gate died with
#   can't open file '<consumer>/ops/scripts/validate_commit_verification_contract.py'
# on a hook that had checked nothing — a false FAIL blocking `make pr` for every
# consumer repository.
#
# NOTE (still deferred): cwd=$GOV_ROOT with absolute --files paths. That changes
# how every hook resolves its inputs; skipping the unresolvable hooks is the
# narrower fix for the failure actually observed.
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

# Corpus + generated heal + desktop wiring (gate owns check_governance_wiring.sh).
# Pre-commit ruff/ruff-format are skipped: locked-venv ruff is the one writer.
_CORPUS_SKIP="sync-generated-artifacts,repo-hygiene,legacy-doctrine-residue,rules-check,skills-check,symlinks-check,ruff,ruff-format"
_READER_HOOKS="check-merge-conflict,check-added-large-files,check-yaml,no-hardcoded-paths,gh-package-deps-preflight"
_WRITER_HOOKS="end-of-file-fixer,trailing-whitespace"
# Writer pass skips every reader. Reader pass skips every writer. Disjoint.
_WRITER_SKIP="${_CORPUS_SKIP},${_READER_HOOKS}"
_READER_SKIP="${_CORPUS_SKIP},${_WRITER_HOOKS}"

# Governance-local hooks with no `files:` guard. Their entry scripts live in the
# governance tree, so in a consumer workspace they resolve to a path that does
# not exist and the hook dies on a missing file rather than on anything it
# checked. `symlinks-check` and `legacy-doctrine-residue` are already in
# _CORPUS_SKIP; `commit-verification-contract` was not, and is the one that
# actually failed. Skipped ONLY for a consumer workspace — the governance repo
# guards its own commit-verification contract exactly as before, which is the
# whole point of that hook.
_GOV_ONLY_SKIP="commit-verification-contract"
if [[ "$WS" != "$GOV_ROOT" ]]; then
  _WRITER_SKIP="${_WRITER_SKIP},${_GOV_ONLY_SKIP}"
  _READER_SKIP="${_READER_SKIP},${_GOV_ONLY_SKIP}"
fi

_run_kernel() {
  local _kernel_py="$GOV_ROOT/.venv/bin/python"
  if [[ ! -x "$_kernel_py" ]]; then
    _kernel_py="$(command -v python3)"
  fi
  if [[ -f "$GOV_ROOT/ops/autonomy/kernel_gate.py" ]]; then
    echo "--- kernel hook (before pre-commit / ruff) ---"
    "$_kernel_py" "$GOV_ROOT/ops/autonomy/kernel_gate.py" precommit \
      --workspace "$WS" --gov-root "$GOV_ROOT" --changed-file "$tmp" || return $?
  fi
  return 0
}

_run_hooks() {
  local skip="$1" rc=0
  set +e
  SKIP="$skip" pre-commit run --config "$GOV_PRECOMMIT_CONFIG" --files "${files[@]}"
  rc=$?
  set -e
  return "$rc"
}

_run_locked_ruff_writer() {
  echo "--- ruff (locked writer) ---"
  py_list="$(mktemp)"
  if [[ -n "${PR_CHANGED_FILE:-}" && "$tmp" == "$PR_CHANGED_FILE" ]]; then
    trap 'rm -f "$py_list"' EXIT
  else
    trap 'rm -f "$tmp" "$py_list"' EXIT
  fi
  grep -E '\.(py|pyi)$' "$tmp" >"$py_list" || true
  if [[ ! -s "$py_list" ]]; then
    echo "OK: no changed Python files for ruff"
    return 0
  fi
  echo "ruff (changed): $(grep -c . "$py_list") file(s)"
  local _ruff="$GOV_ROOT/.venv/bin/ruff"
  if [[ ! -x "$_ruff" && -n "${GOV_TOOLCHAIN_ROOT:-}" && -x "$GOV_TOOLCHAIN_ROOT/.venv/bin/ruff" ]]; then
    _ruff="$GOV_TOOLCHAIN_ROOT/.venv/bin/ruff"
  fi
  if [[ ! -x "$_ruff" ]]; then
    echo "FAIL: locked ruff missing at $GOV_ROOT/.venv/bin/ruff (run: make venv)" >&2
    return 1
  fi
  xargs "$_ruff" check --fix <"$py_list"
  xargs "$_ruff" format <"$py_list"
}

_hard_stop_tracked_dirt() {
  # Staged mode is a commit IN PROGRESS: its staged changes are tracked files
  # that `git status --porcelain` reports as dirty by definition. Applying the
  # clean-tree assertion there rejects every commit, which is precisely what the
  # governed shim installed by ops/scripts/install_commit_hook.sh would do.
  #
  # The guard was inline before this check became a function and was dropped in
  # the extraction (e3f7065, #347). tests/ops/autonomy/test_verification_bypass_gate.py
  # ::test_runner_supports_staged_mode has been failing on main ever since.
  if [[ "$PR_STAGED" != "1" ]] && git status --porcelain | grep -qvE '^\?\?'; then
    echo "FAIL: tracked files dirty after precommit-repo — commit the rewrite, then re-run."
    echo "      Do not auto-stage. Paths:"
    git status --porcelain | grep -vE '^\?\?'
    return 1
  fi
  return 0
}

if [[ "$STAGE" == "readers" ]]; then
  echo "--- pre-commit readers (once) ---"
  _run_hooks "$_READER_SKIP" && pc_rc=0 || pc_rc=$?
  if [[ "$pc_rc" -ne 0 ]]; then
    echo "FAIL: pre-commit readers exited ${pc_rc}" >&2
    exit "$pc_rc"
  fi
  echo "OK: precommit readers clean"
  exit 0
fi

# writers or unset (standalone): kernel first, never from the reader invocation.
_run_kernel || exit $?

echo "--- pre-commit writers (once) ---"
_run_hooks "$_WRITER_SKIP" && pc_rc=0 || pc_rc=$?

_run_locked_ruff_writer || exit $?
_hard_stop_tracked_dirt || exit $?

if [[ "$pc_rc" -ne 0 ]]; then
  echo "FAIL: pre-commit writers exited ${pc_rc}" >&2
  exit "$pc_rc"
fi

if [[ "$STAGE" == "writers" ]]; then
  echo "OK: precommit writers clean (kernel + writers + locked ruff, no tracked dirt)"
  exit 0
fi

echo "--- pre-commit readers (once) ---"
_run_hooks "$_READER_SKIP" && pc_rc=0 || pc_rc=$?
if [[ "$pc_rc" -ne 0 ]]; then
  echo "FAIL: pre-commit readers exited ${pc_rc}" >&2
  exit "$pc_rc"
fi

echo "OK: precommit-repo clean (hooks + locked ruff, no tracked dirt)"
