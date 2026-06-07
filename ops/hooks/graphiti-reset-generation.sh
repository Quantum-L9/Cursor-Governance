#!/usr/bin/env bash
# Task-scoped reset of memory_satisfied_for when task signature changes
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
# shellcheck source=graphiti_common.sh
source "$(dirname "$REAL_HOOK")/graphiti_common.sh"
graphiti_gates_enabled || exit 0
STATE="$(graphiti_state_file)"
mkdir -p "$(dirname "$STATE")"
INPUT="$(cat)"
export HOOK_INPUT="$INPUT"
export STATE_PATH="$STATE"
python3 - <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

raw = os.environ.get("HOOK_INPUT", "")
prompt = ""
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
    except json.JSONDecodeError:
        prompt = raw[:500]
if not prompt:
    prompt = os.environ.get("CURSOR_USER_MESSAGE", "")[:500]

state_path = Path(os.environ["STATE_PATH"])
data = {}
if state_path.is_file():
    data = json.loads(state_path.read_text(encoding="utf-8"))
new_sig = hashlib.sha256(prompt.encode()).hexdigest()[:16]
if data.get("task_signature") != new_sig:
    data["task_signature"] = new_sig
    data["memory_satisfied_for"] = []
    state_path.write_text(json.dumps(data, indent=2) + "\n")
PY
exit 0
