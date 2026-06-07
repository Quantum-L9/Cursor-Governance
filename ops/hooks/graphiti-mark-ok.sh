#!/usr/bin/env bash
# Mark memory satisfied after Graphiti MCP tool use
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
# shellcheck source=graphiti_common.sh
source "$(dirname "$REAL_HOOK")/graphiti_common.sh"
graphiti_gates_enabled || exit 0
INPUT="${1:-}"
echo "$INPUT" | grep -qi graphiti || exit 0
STATE="$(graphiti_state_file)"
[ -f "$STATE" ] || exit 0
python3 - <<PY
import json
from pathlib import Path
p = Path("$STATE")
d = json.loads(p.read_text())
sig = d.get("task_signature")
if sig and sig not in d.setdefault("memory_satisfied_for", []):
    d["memory_satisfied_for"].append(sig)
p.write_text(json.dumps(d, indent=2) + "\n")
PY
exit 0
