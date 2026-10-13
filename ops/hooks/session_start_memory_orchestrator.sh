#!/usr/bin/env bash
# sessionStart — code-graph health + canonical memory hydrate packet.
# Emits hydrate_markdown + codegraph_markdown + additional_context (JSON).
# Resume SSOT is the canonical memory control plane (ops/memory) — never
# memory-bank, and since stage C8 never a provider call.
set -uo pipefail

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
# shellcheck source=graphiti_common.sh
source "$HOOK_DIR/graphiti_common.sh"

REPO="${CURSOR_PROJECT_DIR:-}"

export L9_MEMORY_AGENT_ID="${L9_MEMORY_AGENT_ID:-cursor}"
export USER_ID="${USER_ID:-cursor_agent}"
# SessionStart owns session_id (once per session). conversation_id is a later
# chat key and must not become the session id — that lets every agent share one
# write-gate pass.
if [ -z "${CURSOR_SESSION_ID:-}" ] || [ "${CURSOR_SESSION_ID}" = "default" ]; then
  _HOOK_SID="$(python3 -c '
import json, os
raw = os.environ.get("L9_HOOK_PAYLOAD", "")
try:
    data = json.loads(raw) if raw.strip() else {}
except (json.JSONDecodeError, TypeError):
    data = {}
sid = ""
if isinstance(data, dict):
    sid = str(data.get("session_id") or data.get("sessionId") or "").strip()
print(sid if sid and sid != "default" else "")
' 2>/dev/null || true)"
  if [ -n "$_HOOK_SID" ]; then
    export CURSOR_SESSION_ID="$_HOOK_SID"
  fi
  unset _HOOK_SID
fi
export CURSOR_SESSION_ID="${CURSOR_SESSION_ID:-default}"
if [ -z "${CURSOR_CONVERSATION_ID:-}" ] || [ "${CURSOR_CONVERSATION_ID}" = "default" ]; then
  _HOOK_CID="$(python3 -c '
import json, os
raw = os.environ.get("L9_HOOK_PAYLOAD", "")
try:
    data = json.loads(raw) if raw.strip() else {}
except (json.JSONDecodeError, TypeError):
    data = {}
cid = ""
if isinstance(data, dict):
    cid = str(data.get("conversation_id") or data.get("conversationId") or "").strip()
print(cid if cid and cid != "default" else "")
' 2>/dev/null || true)"
  if [ -n "$_HOOK_CID" ]; then
    export CURSOR_CONVERSATION_ID="$_HOOK_CID"
  fi
  unset _HOOK_CID
fi
export CURSOR_CONVERSATION_ID="${CURSOR_CONVERSATION_ID:-}"

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

# Open latch is local visibility (ADR-0028). Write it even when Graphiti is disabled
# so a later enabled session can still see the skipped_disabled close-gap.
PY="${GOV_ROOT}/.venv/bin/python3"
[ -x "$PY" ] || PY="python3"

# ONE lifecycle id, resolved before the open latch (audit P573-F2).
# SessionStart is the only hook that knows a new session began: when the
# payload carried no session id (Cursor's conversation-only payload) the id is
# generated HERE, once, persisted under .l9/memory/session.json, and handed to
# the open latch below (and to sessionEnd close) — never "default" for the
# latch while another stage invents a UUID of its own. A real id (env or
# payload) passes through unchanged; rotate=True means a pointer left by a
# previous session is never reused, so previous_opened.json rotates and a
# missed close surfaces as a close-gap. Persistence is fail-open; a resolver
# fault keeps the default.
if [ -n "$REPO" ] && [ -f "$GOV_ROOT/ops/graphiti/hydration/session_latches.py" ]; then
  _LIFECYCLE_SID="$(cd "$GOV_ROOT" && PYTHONPATH="$GOV_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    "$PY" -c 'import sys; from ops.graphiti.hydration.session_latches import resolve_or_create_session_id; print(resolve_or_create_session_id(sys.argv[1], explicit=sys.argv[2], rotate=True, conversation_id=sys.argv[3]))' \
    "$REPO" "$CURSOR_SESSION_ID" "$CURSOR_CONVERSATION_ID" 2>/dev/null || true)"
  if [ -n "$_LIFECYCLE_SID" ]; then
    export CURSOR_SESSION_ID="$_LIFECYCLE_SID"
  fi
  unset _LIFECYCLE_SID
fi

if [ -n "$REPO" ] && [ -f "$GOV_ROOT/ops/graphiti/hydration/cli.py" ]; then
  BG_OPEN=()
  if [ "${CURSOR_IS_BACKGROUND_AGENT:-}" = "1" ] || [ "${L9_MEMORY_BACKGROUND:-}" = "1" ]; then
    BG_OPEN+=(--background)
  fi
  (cd "$GOV_ROOT" && PYTHONPATH="$GOV_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    "$PY" -m ops.graphiti.hydration.cli open \
    --project-dir "$REPO" --session-id "$CURSOR_SESSION_ID" \
    "${BG_OPEN[@]}" >/dev/null 2>&1) || true
fi

# SessionStart is memory HEALTH-ONLY (2026-10-13): one bounded health call,
# no hydrate / search / conflicts / packet compile, no resume content. The
# session identity, open latch and code-graph diagnostics above are unchanged.
# Retrieval is on demand: python -m ops.memory.cli hydrate "<task>" --workspace <repo>.
# Output lines use classify_hydrate_state.py's markers so the runtime report
# stays truthful: DEGRADED (memory ran, unhealthy) / ENVIRONMENT_FAULT (never
# reached memory).
if graphiti_enabled; then
  if [ -f "$GOV_ROOT/ops/memory/cli.py" ]; then
    HYDRATE_MD="$(cd "$GOV_ROOT" && PYTHONPATH="$GOV_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
      "$PY" -c '
import json, subprocess, sys
from ops.memory.control_plane_client import fault_class_for

on_demand = "on demand: python -m ops.memory.cli hydrate \"<task>\" --workspace <repo>"
try:
    proc = subprocess.run(
        [sys.executable, "-m", "ops.memory.cli", "--surface", "cursor-session-start",
         "--timeout", "10", "health"],
        capture_output=True, text=True, timeout=15, check=False,
    )
    doc = json.loads(proc.stdout or "{}")
except (subprocess.TimeoutExpired, ValueError) as exc:
    doc = {"status": "TIMEOUT" if isinstance(exc, subprocess.TimeoutExpired) else "INVALID_RECEIPT",
           "error": type(exc).__name__}
status = str(doc.get("status") or "UNKNOWN").rsplit(".", 1)[-1]
print("### memory status")
print("- SessionStart is health-only: no records read, nothing hydrated")
if doc.get("ok"):
    print("- memory health: OK")
elif fault_class_for(status) == "environment":
    print("ENVIRONMENT_FAULT memory runtime did not answer health (%s)" % status)
    print("REPAIR: make memory-readiness")
else:
    print("DEGRADED memory health %s: %s" % (status, str(doc.get("error") or "")[:200]))
print("- " + on_demand)
' 2>/dev/null || printf '%s\n' '### memory status' 'DEGRADED memory health check failed to run' '- on demand: python -m ops.memory.cli hydrate "<task>" --workspace <repo>')"
  else
    HYDRATE_MD="$(printf '%s\n' '### memory status' 'ENVIRONMENT_FAULT memory CLI missing (ops/memory/cli.py)' 'REPAIR: make memory-readiness')"
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
