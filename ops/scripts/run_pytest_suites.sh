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
if [[ -x "$ROOT/.venv/bin/python" ]] && "$ROOT/.venv/bin/python" -c 'import pytest' 2>/dev/null; then
  exec "$ROOT/.venv/bin/python" "$RUNNER" --profile local -- "$@"
fi
echo "FAIL: locked .venv missing pytest — uv sync --locked --extra dev" >&2
exit 2
