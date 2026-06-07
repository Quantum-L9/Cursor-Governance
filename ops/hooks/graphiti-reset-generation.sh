#!/usr/bin/env bash
# Task-scoped reset of memory_satisfied_for when task signature changes
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
# shellcheck source=graphiti_common.sh
source "$(dirname "$REAL_HOOK")/graphiti_common.sh"
graphiti_gates_enabled || exit 0
STATE="$(graphiti_state_file)"
[ -f "$STATE" ] || exit 0
python3 - <<PY
import json, hashlib, os, sys
from pathlib import Path
state_path = Path("$STATE")
data = json.loads(state_path.read_text())
prompt = os.environ.get("CURSOR_USER_MESSAGE", "")[:500]
new_sig = hashlib.sha256(prompt.encode()).hexdigest()[:16]
if data.get("task_signature") != new_sig:
    data["task_signature"] = new_sig
    data["memory_satisfied_for"] = []
    state_path.write_text(json.dumps(data, indent=2) + "\n")
PY
exit 0
