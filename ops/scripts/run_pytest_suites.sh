#!/usr/bin/env bash
# Compatibility wrapper — historical entrypoint for `make test` / `make pr-full`.
#
# Suite topology is NOT defined here. The single source of truth for which
# suites exist and how they run is ops/config/python-contract.json, executed by
# ops/scripts/run_python_test_suites.py. This wrapper only forwards operator
# pytest arguments to the canonical local profile and preserves its exit code.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# Prefer the locked environment when it exists, so make test / make pr-full run
# the exact pinned interpreter and dependencies (same as `make venv`).
if command -v uv >/dev/null 2>&1 && [[ -x "$ROOT/.venv/bin/python" || -f "$ROOT/uv.lock" ]]; then
  uv run --no-build python ops/scripts/run_python_test_suites.py --profile local -- "$@"
else
  python3 ops/scripts/run_python_test_suites.py --profile local -- "$@"
fi
