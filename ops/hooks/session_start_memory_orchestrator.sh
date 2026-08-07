#!/usr/bin/env bash
# sessionStart — code-graph health + Graphiti prefetch; single additional_context blob
set -uo pipefail

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
# shellcheck source=graphiti_common.sh
source "$HOOK_DIR/graphiti_common.sh"

REPO="${CURSOR_PROJECT_DIR:-}"
PARTS=()

# Code-graph segment (PlasticOS only)
if [ -n "$REPO" ] && [ -d "$REPO/plasticos_base" ] && [ -x "$HOOK_DIR/code-graph-health.sh" ] || [ -L "$HOME/.cursor/hooks/code-graph-health.sh" ]; then
  CG_OUT="$(CURSOR_PROJECT_DIR="$REPO" bash "$HOME/.cursor/hooks/code-graph-health.sh" 2>/dev/null || true)"
  CG_CTX="$(echo "$CG_OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('additional_context',''))" 2>/dev/null || true)"
  [ -n "$CG_CTX" ] && PARTS+=("$CG_CTX")
fi

# Graphiti inject/PICKUP is the resume SSOT (memory-bank deprecated).
graphiti_load_env
if graphiti_enabled; then
  graphiti_resolve_cli
  if [ -f "$GRAPHITI_CLI" ]; then
    graphiti_load_env
    export CURSOR_CONVERSATION_ID="${CURSOR_CONVERSATION_ID:-default}"
    if OUT="$(python3 "$GRAPHITI_CLI" inject "session start" 2>/dev/null)"; then
      GID="$(echo "$OUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('group_id',''))" 2>/dev/null || true)"
      PARTS+=("graphiti: prefetch ok group_id=${GID:-unknown}. Rule 03-graphiti-memory; skill l9-graphiti-memory.")
    else
      PARTS+=("graphiti: prefetch degraded — resume via PICKUP search when online; VPS may be down.")
    fi
  else
    PARTS+=("graphiti: CLI missing — resume via PICKUP search when online")
  fi
else
  PARTS+=("graphiti: disabled — no memory-bank fallback (deprecated)")
fi

COMBINED="$(printf '%s | ' "${PARTS[@]}")"
COMBINED="${COMBINED% | }"

python3 - <<PY
import json, os
print(json.dumps({
    "env": {
        "GRAPHITI_MEMORY_ENABLED": os.environ.get("GRAPHITI_MEMORY_ENABLED", "1"),
        "GRAPHITI_WRITE_GATES": os.environ.get("GRAPHITI_WRITE_GATES", "0"),
    },
    "additional_context": """${COMBINED}""",
}))
PY
exit 0
