#!/usr/bin/env bash
# sessionStart — code-graph health + Graphiti hydrate packet.
# Emits hydrate_markdown + codegraph_markdown + additional_context (JSON).
# Resume SSOT is Graphiti only — never memory-bank.
set -uo pipefail

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
# shellcheck source=graphiti_common.sh
source "$HOOK_DIR/graphiti_common.sh"

REPO="${CURSOR_PROJECT_DIR:-}"

export L9_MEMORY_AGENT_ID="${L9_MEMORY_AGENT_ID:-cursor}"
export USER_ID="${USER_ID:-cursor_agent}"
export CURSOR_CONVERSATION_ID="${CURSOR_CONVERSATION_ID:-${CURSOR_SESSION_ID:-default}}"

CODEGRAPH_MD="skipped"
if [ -n "$REPO" ] && [ -d "$REPO/plasticos_base" ]; then
  CG_HOOK="$HOME/.cursor/hooks/code-graph-health.sh"
  if [ -x "$HOOK_DIR/code-graph-health.sh" ] || [ -x "$CG_HOOK" ] || [ -L "$CG_HOOK" ]; then
    CG_OUT="$(CURSOR_PROJECT_DIR="$REPO" bash "$CG_HOOK" 2>/dev/null || true)"
    CODEGRAPH_MD="$(echo "$CG_OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('additional_context','') or 'skipped')" 2>/dev/null || echo "skipped")"
    [ -n "$CODEGRAPH_MD" ] || CODEGRAPH_MD="skipped"
  fi
fi

graphiti_load_env
GOV_ROOT="$(cd "$(dirname "$REAL_HOOK")/../.." && pwd)"
if [ ! -f "$GOV_ROOT/ops/graphiti/hydration/cli.py" ]; then
  GOV_ROOT="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
fi

HYDRATE_MD="Graphiti disabled — no resume memory"

if graphiti_enabled; then
  if [ -n "$REPO" ] && [ -f "$GOV_ROOT/ops/graphiti/hydration/cli.py" ]; then
    PY="${GOV_ROOT}/.venv/bin/python3"
    [ -x "$PY" ] || PY="python3"
    if OUT="$(cd "$GOV_ROOT" && PYTHONPATH="$GOV_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
        "$PY" -m ops.graphiti.hydration.cli compile \
        --project-dir "$REPO" \
        --session-id "$CURSOR_CONVERSATION_ID" \
        --agent-id "$L9_MEMORY_AGENT_ID" \
        --format json 2>/dev/null)"; then
      HYDRATE_MD="$(echo "$OUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print("hydration degraded — resume via PICKUP search when online; next=")
    raise SystemExit(0)
ctx = d.get("additional_context") or ""
pkt = d.get("packet") or {}
stats = pkt.get("hydrate_stats") or {}
if ctx.strip():
    print(ctx)
else:
    print(
        "graphiti hydrate: group_id=%s agent_id=%s facts_returned=%s pickup_parsed=%s"
        % (
            pkt.get("group_id", "unresolved"),
            pkt.get("agent_id", ""),
            stats.get("facts_returned", 0),
            "yes" if stats.get("pickup_parsed") else "no",
        )
    )
' 2>/dev/null || echo "hydration degraded — resume via PICKUP search when online; next=")"
    else
      HYDRATE_MD="hydration degraded — resume via PICKUP search when online; next="
      graphiti_resolve_cli
      if [ -f "$GRAPHITI_CLI" ]; then
        if OUT="$(cd "$REPO" && python3 "$GRAPHITI_CLI" inject "session start" 2>/dev/null)"; then
          GID="$(echo "$OUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('group_id',''))" 2>/dev/null || true)"
          HYDRATE_MD="${HYDRATE_MD}
graphiti: prefetch receipt ok group_id=${GID:-unknown}"
        fi
      fi
    fi
    # Preserve inject/state hash for gates even when hydrate succeeds
    graphiti_resolve_cli
    if [ -f "$GRAPHITI_CLI" ]; then
      (cd "$REPO" && python3 "$GRAPHITI_CLI" inject "session start" >/dev/null 2>&1) || true
    fi
  else
    HYDRATE_MD="hydrate CLI missing — resume via PICKUP search when online; next="
  fi
else
  HYDRATE_MD="Graphiti disabled — no resume memory"
fi

# Never emit memory-bank as a resume path
HYDRATE_MD="$(printf '%s' "$HYDRATE_MD" | sed 's/memory-bank/Graphiti/g')"
COMBINED="$(printf '%s\n---\n%s' "$HYDRATE_MD" "$CODEGRAPH_MD")"

HYDRATE_MD="$HYDRATE_MD" CODEGRAPH_MD="$CODEGRAPH_MD" COMBINED="$COMBINED" python3 - <<'PY'
import json, os
print(json.dumps({
    "env": {
        "GRAPHITI_MEMORY_ENABLED": os.environ.get("GRAPHITI_MEMORY_ENABLED", "1"),
        "GRAPHITI_WRITE_GATES": os.environ.get("GRAPHITI_WRITE_GATES", "0"),
        "L9_MEMORY_AGENT_ID": os.environ.get("L9_MEMORY_AGENT_ID", "cursor"),
        "USER_ID": os.environ.get("USER_ID", "cursor_agent"),
    },
    "hydrate_markdown": os.environ.get("HYDRATE_MD", ""),
    "codegraph_markdown": os.environ.get("CODEGRAPH_MD", "skipped"),
    "additional_context": os.environ.get("COMBINED", ""),
}))
PY
exit 0
