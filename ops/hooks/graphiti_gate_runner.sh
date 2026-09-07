#!/usr/bin/env bash
# Run graphiti_gate_lib.py (canonical session-state gate, stage C8) with
# failClosed when the write gates are enabled (L9_MEMORY_WRITE_GATES=1; the
# legacy GRAPHITI_WRITE_GATES name is honored until C9).
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
# shellcheck source=graphiti_common.sh
source "$HOOK_DIR/graphiti_common.sh"
MODE="${1:?mode required}"
ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
GATE_LIB="$ROOT/ops/graphiti/graphiti_gate_lib.py"
if [ ! -f "$GATE_LIB" ]; then
  ROOT="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
  GATE_LIB="$ROOT/ops/graphiti/graphiti_gate_lib.py"
fi
if [ -x "$ROOT/.venv/bin/python3" ]; then PY="$ROOT/.venv/bin/python3"; else PY="$(command -v python3)"; fi
INPUT="$(cat)"
DENY_MSG='{"permission":"deny","user_message":"Memory gate error — failClosed"}'
if [ ! -f "$GATE_LIB" ]; then
  if graphiti_gates_enabled; then
    echo "$DENY_MSG"
    exit 0
  fi
  echo '{"permission":"allow"}'
  exit 0
fi
if OUT="$(PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" "$GATE_LIB" "$MODE" <<< "$INPUT" 2>&1)"; then
  echo "$OUT"
  exit 0
fi
if graphiti_gates_enabled; then
  echo "$DENY_MSG"
else
  echo '{"permission":"allow"}'
fi
exit 0
