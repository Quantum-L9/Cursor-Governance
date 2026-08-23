#!/usr/bin/env bash
# subagentStop: capture raw result, correlate it, and hand it to generated-data.
set -uo pipefail
set +x
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
if [ -x "$ROOT/.venv/bin/python3" ]; then
  PY="$ROOT/.venv/bin/python3"
else
  PY="$(command -v python3)"
fi
PAYLOAD="${CURSOR_SUBAGENT_STOP_JSON:-{\"assignment_id\":\"${CURSOR_SUBAGENT_ASSIGNMENT_ID:-}\"}}"
REPORT="$(echo "$PAYLOAD" | "$PY" -m environment.agents.lifecycle.compose_stop)"
RC=$?
printf '%s\n' "$REPORT"
if [ "$RC" -ne 0 ]; then
  echo "ERROR: subagent result was returned but generated-data capture/processing failed; inspect the emitted receipts" >&2
  exit "$RC"
fi
exit 0
