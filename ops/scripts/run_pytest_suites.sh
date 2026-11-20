#!/usr/bin/env bash
# Compatibility wrapper — delegates to the canonical registry-driven Python runner.
#
# Suite topology lives ONLY in ops/config/python-contract.json and is executed by
# ops/scripts/run_python_test_suites.py. This wrapper exists so make test / make
# pr-full and any historical caller keep working; it re-implements no suite
# definitions. All user-supplied pytest arguments are forwarded verbatim to the
# suites that permit argument forwarding.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$(cd "$(dirname "$0")" && pwd)/resolve_governance_paths.sh"
# This script consumes no GOV_ROOT — it sources the file for
# is_l9_isolate_workspace/bind_isolate_toolchain. But that file installs an
# EXIT trap that warns when no entry point ran, so bind explicitly rather
# than emit a warning against a script that is not misusing the resolver.
resolve_governance_paths || true
if is_l9_isolate_workspace "$ROOT"; then
  bind_isolate_toolchain "$ROOT" "${GOV_TOOLCHAIN_ROOT:-$HOME/.cursor-governance}"
fi
TOOL_ROOT="${GOV_TOOLCHAIN_ROOT:-$ROOT}"
cd "$ROOT"

RUNNER="ops/scripts/run_python_test_suites.py"

# Prefer the locked venv (same environment CI and `make venv` produce).
# Never fall back to the ambient interpreter — Homebrew/system python3 lacks
# the pyproject.toml / uv.lock runtime set.
#
# Isolates must not uv sync a new .venv (miniconda / cryptography --no-build).
# pytest lives in the `dev` optional-dependencies extra, which neither
# `uv sync` nor `uv run --no-build` installs by default. Sync the extra first
# so the suite runner never executes with a pytest-less interpreter
# (2026-08-15 factory repair).
if is_l9_isolate_workspace "$ROOT"; then
  if [[ -x "$TOOL_ROOT/.venv/bin/python" ]] && "$TOOL_ROOT/.venv/bin/python" -c 'import pytest' 2>/dev/null; then
    exec "$TOOL_ROOT/.venv/bin/python" "$ROOT/$RUNNER" --profile local -- "$@"
  fi
  echo "FAIL: isolate toolchain missing pytest at $TOOL_ROOT/.venv/bin/python" >&2
  exit 2
fi
bash "$ROOT/ops/scripts/ensure_gov_python.sh" "$ROOT"
# A GitHub Actions pull_request run (Core's required `make test`) tests only the
# PR's changed files. Unknown scope and L9_CI_FULL_SUITE=1 exit nonzero on a
# pull request; they never fall through to the full suite or --profile ci.
# Every other event keeps the non-PR profile. See the helper.
# shellcheck source=lib/ci_pr_scope.sh
source "$ROOT/ops/scripts/lib/ci_pr_scope.sh"
scope_args=()
scope_rc=0
if scope_paths="$(l9_ci_pr_changed_files)"; then
  scope_rc=0
else
  scope_rc=$?
fi
if [[ "$scope_rc" -ne 0 ]]; then
  if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" || "$scope_rc" -ge 2 ]]; then
    echo "FAIL: pull-request scope status ${scope_rc}; full suite refused" >&2
    exit "$scope_rc"
  fi
elif [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" && -z "$scope_paths" ]]; then
  echo "PR_SCOPE_UNKNOWN: no changed path remains on HEAD; full suite refused" >&2
  exit 2
fi
if [[ "$scope_rc" -eq 0 ]]; then
  scope_file="$(mktemp "${TMPDIR:-/tmp}/l9-ci-scope.XXXXXX")"
  if [[ -n "$scope_paths" ]]; then
    printf '%s\n' "$scope_paths" >"$scope_file"
  fi
  scope_args=(--changed-file "$scope_file")
fi
if [[ -x "$ROOT/.venv/bin/python" ]] && "$ROOT/.venv/bin/python" -c 'import pytest' 2>/dev/null; then
  # The guarded expansion keeps an empty array safe under `set -u` on bash 3.2.
  exec "$ROOT/.venv/bin/python" "$RUNNER" --profile local ${scope_args[@]+"${scope_args[@]}"} -- "$@"
fi
echo "FAIL: locked .venv missing pytest — uv sync --locked --extra dev" >&2
exit 2
