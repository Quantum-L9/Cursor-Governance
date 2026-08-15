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
cd "$ROOT"

RUNNER="ops/scripts/run_python_test_suites.py"

# Prefer the locked venv (same environment CI and `make venv` produce) when it
# exists; otherwise fall back to the ambient interpreter.
#
# pytest lives in the `dev` optional-dependencies extra, which neither
# `uv sync` nor `uv run --no-build` installs by default. Sync the extra first
# so the suite runner never executes with a pytest-less interpreter
# (2026-08-15 factory repair).
if command -v uv >/dev/null 2>&1 && [[ -x "$ROOT/.venv/bin/python" || -f "$ROOT/uv.lock" ]]; then
  uv sync --extra dev --quiet || true
  if [[ -x "$ROOT/.venv/bin/python" ]] && "$ROOT/.venv/bin/python" -c 'import pytest' 2>/dev/null; then
    exec "$ROOT/.venv/bin/python" "$RUNNER" --profile local -- "$@"
  fi
fi
exec python3 "$RUNNER" --profile local -- "$@"
