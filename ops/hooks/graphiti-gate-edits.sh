#!/usr/bin/env bash
# preToolUse — failClosed Write when GRAPHITI_WRITE_GATES=1
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
exec "$(dirname "$REAL_HOOK")/graphiti_gate_runner.sh" pre_tool_use
