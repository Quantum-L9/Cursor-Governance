#!/usr/bin/env bash
# subagentStart — inherit parent memory satisfaction
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
# shellcheck source=graphiti_common.sh
source "$(dirname "$REAL_HOOK")/graphiti_common.sh"
graphiti_resolve_cli
GATE_LIB="$(dirname "$GRAPHITI_CLI")/graphiti_gate_lib.py"
INPUT="$(cat)"
if [ ! -f "$GATE_LIB" ]; then
  echo '{"permission":"allow"}'
  exit 0
fi
python3 "$GATE_LIB" subagent <<< "$INPUT" 2>/dev/null || echo '{"permission":"allow"}'
exit 0
