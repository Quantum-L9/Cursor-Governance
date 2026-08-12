#!/usr/bin/env bash
# subagentStop — emit SubagentReturnReceipt when assignment_id is known.
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
if [ -x "$ROOT/.venv/bin/python3" ]; then PY="$ROOT/.venv/bin/python3"; else PY="$(command -v python3)"; fi
PAYLOAD="${CURSOR_SUBAGENT_STOP_JSON:-{"assignment_id":"${CURSOR_SUBAGENT_ASSIGNMENT_ID:-}"}}"
echo "$PAYLOAD" | "$PY" -m environment.agents.lifecycle.compose_stop || true
exit 0
