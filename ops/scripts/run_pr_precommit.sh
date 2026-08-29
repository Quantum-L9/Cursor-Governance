#!/usr/bin/env bash
# INTERNAL leaf of make pr (run_pr_gate.sh). Diagnose: OPEN_PR=0 make pr
# (leftover target pr-check is the same leaf). Runs the hook catalog in
# changed files only. This is not a public gate and not a git commit hook.
# Full-tree of the same catalog is INTERNAL `make precommit` (nightly / make pr-full).
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
# Staged mode: invoked from a git commit hook rather than from make pr.
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
# against a real consumer checkout (not available in this environment), so it
# is not enabled here; the explicit config binding is the safe, in-repo-validated
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
  echo "FAIL: pre-commit CLI missing (INTERNAL leaf of make pr)." >&2
  echo "      Install the framework: pipx install pre-commit" >&2
  echo "      Do not run 'pre-commit install' — this repo has no git commit hook." >&2
  echo "      Public ceremony: make pr (Diagnose: OPEN_PR=0 make pr)." >&2
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
  # Commit-hook staged mode rewrites the worktree on purpose; the shim stages
  # those bytes. Skip the dirty-tree hard-stop so a governed hook can finish.
  if [[ "$PR_STAGED" != "1" ]]; then
    if git status --porcelain | grep -qvE '^\?\?'; then
      echo "FAIL: tracked files dirty after precommit-repo — commit the rewrite, then re-run."
      echo "      Do not auto-stage. Paths:"
      git status --porcelain | grep -vE '^\?\?'
      return 1
    fi
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
