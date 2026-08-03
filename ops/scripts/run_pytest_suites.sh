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
if command -v uv >/dev/null 2>&1 && [[ -x "$ROOT/.venv/bin/python" || -f "$ROOT/uv.lock" ]]; then
  exec uv run --no-build python "$RUNNER" --profile local -- "$@"
else
  exec python3 "$RUNNER" --profile local -- "$@"
fi
