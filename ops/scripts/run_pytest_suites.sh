#!/usr/bin/env bash
# Run pytest for both autonomy packages without import shadowing.
#
# Root `autonomy/` (W7 control plane) and `environment/claude-code/autonomy/`
# (Claude Code bounded-concurrency runtime) share the top-level package name.
# A single `PYTHONPATH=. pytest .` therefore collects Claude Code tests under
# the wrong package. Split into two suites:
#   1) repo suite with root autonomy on PYTHONPATH (Claude suite ignored)
#   2) Claude Code suite with environment/claude-code on PYTHONPATH
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PYTEST_ARGS=("$@")
if [[ ${#PYTEST_ARGS[@]} -eq 0 ]]; then
  PYTEST_ARGS=(--tb=short -q)
fi

run_pytest() {
  if command -v uv >/dev/null 2>&1 && [[ -x "$ROOT/.venv/bin/python" || -f "$ROOT/uv.lock" ]]; then
    uv run --no-build pytest "$@"
  else
    pytest "$@"
  fi
}

status=0

echo "--- pytest: repo suite (root autonomy) ---"
TESTING=true PYTHONPATH="$ROOT" run_pytest . \
  --ignore=environment/claude-code/autonomy \
  "${PYTEST_ARGS[@]}" || status=$?
if [[ "$status" -eq 5 ]]; then
  echo "OK: repo suite collected zero tests (exit 5)"
  status=0
elif [[ "$status" -ne 0 ]]; then
  exit "$status"
fi

echo "--- pytest: Claude Code autonomy suite ---"
TESTING=true PYTHONPATH="$ROOT/environment/claude-code" run_pytest \
  environment/claude-code/autonomy/tests \
  -o addopts= \
  "${PYTEST_ARGS[@]}" || status=$?
if [[ "$status" -eq 5 ]]; then
  echo "OK: Claude Code suite collected zero tests (exit 5)"
  status=0
fi
exit "$status"
