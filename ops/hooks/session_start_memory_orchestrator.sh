#!/usr/bin/env bash
# sessionStart — code-graph health + Graphiti hydrate packet; single additional_context blob
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

# Cursor writer identity for hydrate + any follow-on writes in-session
export L9_MEMORY_AGENT_ID="${L9_MEMORY_AGENT_ID:-cursor}"
export USER_ID="${USER_ID:-cursor_agent}"
export CURSOR_CONVERSATION_ID="${CURSOR_CONVERSATION_ID:-${CURSOR_SESSION_ID:-default}}"

# Graphiti SessionHydrationPacket (facts + next=) — resume SSOT
graphiti_load_env
GOV_ROOT="$(cd "$(dirname "$REAL_HOOK")/../.." && pwd)"
# When installed under ~/.cursor/hooks, resolve SSOT via common helper / symlink
if [ ! -f "$GOV_ROOT/ops/graphiti/hydration/cli.py" ]; then
  GOV_ROOT="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
fi
HYDRATE_CTX=""
if graphiti_enabled; then
  if [ -n "$REPO" ] && [ -f "$GOV_ROOT/ops/graphiti/hydration/cli.py" ]; then
    PY="${GOV_ROOT}/.venv/bin/python3"
    [ -x "$PY" ] || PY="python3"
    if OUT="$(cd "$GOV_ROOT" && PYTHONPATH="$GOV_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
        "$PY" -m ops.graphiti.hydration.cli compile \
        --project-dir "$REPO" \
        --session-id "$CURSOR_CONVERSATION_ID" \
        --agent-id "$L9_MEMORY_AGENT_ID" \
        --format context 2>/dev/null)"; then
      HYDRATE_CTX="$OUT"
      PARTS+=("$HYDRATE_CTX")
    else
      # Fail-open: still run inject for gate receipts, emit explicit degrade
      PARTS+=("graphiti: hydration degraded — resume via PICKUP search when online; next=")
      graphiti_resolve_cli
      if [ -f "$GRAPHITI_CLI" ]; then
        if OUT="$(cd "$REPO" && python3 "$GRAPHITI_CLI" inject "session start" 2>/dev/null)"; then
          GID="$(echo "$OUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('group_id',''))" 2>/dev/null || true)"
          PARTS+=("graphiti: prefetch receipt ok group_id=${GID:-unknown}")
        fi
      fi
    fi
    # Preserve inject/state hash for gates even when hydrate succeeds
    graphiti_resolve_cli
    if [ -f "$GRAPHITI_CLI" ]; then
      (cd "$REPO" && python3 "$GRAPHITI_CLI" inject "session start" >/dev/null 2>&1) || true
    fi
  else
    PARTS+=("graphiti: hydrate CLI missing — resume via PICKUP search when online; next=")
  fi
else
  PARTS+=("graphiti: disabled — no memory-bank fallback (deprecated); next=")
fi

COMBINED="$(printf '%s\n---\n' "${PARTS[@]}")"
COMBINED="${COMBINED%$'\n---\n'}"

# Emit env identity + additional_context (fail-open always; stdin avoids quote breakage)
COMBINED="$COMBINED" python3 - <<'PY'
import json, os
print(json.dumps({
    "env": {
        "GRAPHITI_MEMORY_ENABLED": os.environ.get("GRAPHITI_MEMORY_ENABLED", "1"),
        "GRAPHITI_WRITE_GATES": os.environ.get("GRAPHITI_WRITE_GATES", "0"),
        "L9_MEMORY_AGENT_ID": os.environ.get("L9_MEMORY_AGENT_ID", "cursor"),
        "USER_ID": os.environ.get("USER_ID", "cursor_agent"),
    },
    "additional_context": os.environ.get("COMBINED", ""),
}))
PY
exit 0
