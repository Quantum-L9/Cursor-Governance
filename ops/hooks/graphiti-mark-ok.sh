#!/usr/bin/env bash
# Mark memory satisfied for the current task after a canonical memory MCP tool
# call (postToolUse stdin JSON). Writes only the local, non-authoritative
# session state (ops/memory/session_state.py); never a provider (stage C8).
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
# shellcheck source=graphiti_common.sh
source "$HOOK_DIR/graphiti_common.sh"
graphiti_gates_enabled || exit 0
ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
[ -f "$ROOT/ops/memory/session_state.py" ] || ROOT="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
if [ -x "$ROOT/.venv/bin/python3" ]; then PY="$ROOT/.venv/bin/python3"; else PY="$(command -v python3)"; fi
export HOOK_INPUT="$(cat)"
export L9_SESSION_FALLBACK="${CURSOR_CONVERSATION_ID:-default}"
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" - <<'PY'
import json
import os

from ops.memory.session_state import mark_satisfied

raw = os.environ.get("HOOK_INPUT", "")
blob = raw.lower()
# Only a canonical memory tool call counts: the package-owned server or one of
# its memory.* tools. Provider tool names are not evidence of anything.
if not any(k in blob for k in ("l9-graphite-memory", "memory.hydrate", "memory.search", "memory.get")):
    raise SystemExit(0)
conv = os.environ.get("L9_SESSION_FALLBACK", "default")
try:
    data = json.loads(raw) if raw.strip() else {}
    conv = str(data.get("conversation_id") or data.get("conversationId") or conv)
except json.JSONDecodeError:
    pass
mark_satisfied(conv)
PY
exit 0
