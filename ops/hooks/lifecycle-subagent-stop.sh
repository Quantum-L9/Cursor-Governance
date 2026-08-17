#!/usr/bin/env bash
# subagentStop — emit SubagentReturnReceipt when assignment_id is known.
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
if [ -x "$ROOT/.venv/bin/python3" ]; then PY="$ROOT/.venv/bin/python3"; else PY="$(command -v python3)"; fi
# The inner quotes of a nested ${VAR:-default} are consumed by the outer
# quoting, so the fallback used to emit {assignment_id:abc} — not valid JSON,
# so compose_stop's json.loads raised and `|| true` swallowed it. Build the
# JSON with a tool that quotes correctly instead of by string interpolation.
if [ -n "${CURSOR_SUBAGENT_STOP_JSON:-}" ]; then
  PAYLOAD="$CURSOR_SUBAGENT_STOP_JSON"
else
  PAYLOAD="$(ASSIGNMENT_ID="${CURSOR_SUBAGENT_ASSIGNMENT_ID:-}" python3 -c \
    'import json,os; print(json.dumps({"assignment_id": os.environ["ASSIGNMENT_ID"]}))')"
fi
echo "$PAYLOAD" \
  | ( cd "$ROOT" && PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" \
      "$PY" -m environment.agents.lifecycle.compose_stop ) || true
exit 0
