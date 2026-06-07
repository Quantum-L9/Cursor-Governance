#!/usr/bin/env bash
# Run graphiti_gate_lib.py with failClosed when GRAPHITI_WRITE_GATES=1
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
# shellcheck source=graphiti_common.sh
source "$(dirname "$REAL_HOOK")/graphiti_common.sh"
MODE="${1:?mode required}"
GATE_LIB=""
graphiti_resolve_cli
GATE_LIB="$(dirname "$GRAPHITI_CLI")/graphiti_gate_lib.py"
INPUT="$(cat)"
DENY_MSG='{"permission":"deny","user_message":"Graphiti gate error — failClosed"}'
if [ ! -f "$GATE_LIB" ]; then
  if graphiti_gates_enabled; then
    echo "$DENY_MSG"
    exit 0
  fi
  echo '{"permission":"allow"}'
  exit 0
fi
if OUT="$(python3 "$GATE_LIB" "$MODE" <<< "$INPUT" 2>&1)"; then
  echo "$OUT"
  exit 0
fi
if graphiti_gates_enabled; then
  echo "$DENY_MSG"
else
  echo '{"permission":"allow"}'
fi
exit 0
