#!/usr/bin/env bash
# Mark memory satisfied after Graphiti MCP tool use (postToolUse stdin JSON)
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
# shellcheck source=graphiti_common.sh
source "$(dirname "$REAL_HOOK")/graphiti_common.sh"
graphiti_gates_enabled || exit 0
STATE="$(graphiti_state_file)"
[ -f "$STATE" ] || exit 0
export HOOK_INPUT="$(cat)"
export STATE_PATH="$STATE"
python3 - <<'PY'
import json
import os
from pathlib import Path

raw = os.environ.get("HOOK_INPUT", "")
blob = raw.lower()
if not any(k in blob for k in ("graphiti", "add_episode", "search_facts", "search_nodes", "phase-lock")):
    raise SystemExit(0)

p = Path(os.environ["STATE_PATH"])
d = json.loads(p.read_text(encoding="utf-8"))
sig = d.get("task_signature")
if sig and sig not in d.setdefault("memory_satisfied_for", []):
    d["memory_satisfied_for"].append(sig)
p.write_text(json.dumps(d, indent=2) + "\n")
PY
exit 0
