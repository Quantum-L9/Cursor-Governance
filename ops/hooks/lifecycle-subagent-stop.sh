#!/usr/bin/env bash
# Native Cursor subagentStop: preserve the real host payload before result validation.
set -uo pipefail
set +x
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
if [ -x "$ROOT/.venv/bin/python3" ]; then PY="$ROOT/.venv/bin/python3"; else PY="$(command -v python3)"; fi
INPUT="$(cat)"
REPORT="$(printf '%s\n' "$INPUT" | "$PY" -m environment.agents.lifecycle.compose_stop)"
RC=$?
printf '%s\n' "$REPORT"
if [ "$RC" -ne 0 ]; then
  echo "ERROR: native subagent stop evidence was captured but acceptance/ingress did not converge; inspect lifecycle receipts" >&2
  exit "$RC"
fi
exit 0
