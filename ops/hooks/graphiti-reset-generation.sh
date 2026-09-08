#!/usr/bin/env bash
# Task-scoped reset of explicit memory satisfactions when the task signature
# changes (beforeSubmitPrompt). Writes only the local, non-authoritative session
# state (ops/memory/session_state.py); never a provider (stage C8).
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
# shellcheck source=graphiti_common.sh
source "$HOOK_DIR/graphiti_common.sh"
graphiti_gates_enabled || exit 0
ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
[ -f "$ROOT/ops/memory/session_state.py" ] || ROOT="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
if [ -x "$ROOT/.venv/bin/python3" ]; then PY="$ROOT/.venv/bin/python3"; else PY="$(command -v python3)"; fi
INPUT="$(cat)"
export HOOK_INPUT="$INPUT"
export L9_SESSION_FALLBACK="${CURSOR_CONVERSATION_ID:-default}"
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" - <<'PY'
import hashlib
import json
import os

from ops.memory.session_state import set_task_signature

raw = os.environ.get("HOOK_INPUT", "")
prompt = ""
conv = os.environ.get("L9_SESSION_FALLBACK", "default")
if raw.strip():
    try:
        data = json.loads(raw)
        prompt = (
            data.get("prompt")
            or data.get("user_message")
            or data.get("message")
            or data.get("text")
            or ""
        )
        conv = str(data.get("conversation_id") or data.get("conversationId") or conv)
    except json.JSONDecodeError:
        prompt = raw[:500]
if not prompt:
    prompt = os.environ.get("CURSOR_USER_MESSAGE", "")[:500]
set_task_signature(conv, hashlib.sha256(prompt.encode()).hexdigest()[:16])
PY
exit 0
