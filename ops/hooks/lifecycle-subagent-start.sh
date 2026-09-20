#!/usr/bin/env bash
# Native Cursor subagent lifecycle bridge. Host hook JSON arrives on stdin.
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
MODE="${1:-subagent_start}"
INPUT="$(cat)"
if [ -x "$ROOT/.venv/bin/python3" ]; then PY="$ROOT/.venv/bin/python3"; else PY="$(command -v python3)"; fi

if [ "$MODE" = "subagent_start" ]; then
  # Preserve the existing Graphiti subagent gate, but feed it the same host JSON
  # instead of consuming stdin before the lifecycle bridge can see it.
  # Spawn still requires the PARENT session's hydration.
  if ! printf '%s\n' "$INPUT" | "$HOOK_DIR/graphiti_gate_runner.sh" subagent >/dev/null; then
    printf '%s\n' '{"permission":"deny","reason":"Graphiti subagent gate failed"}'
    exit 1
  fi
  # Child prefetch: the write gate keys on this conversation_id, not the parent.
  # Fail-open here; a missed receipt is a write-gate deny, not a spawn deny.
  CHILD_META="$(INPUT="$INPUT" python3 - <<'PY'
import json, os
raw = os.environ.get("INPUT", "")
out = {"conversation_id": "", "project_dir": ""}
try:
    data = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    data = {}
if isinstance(data, dict):
    out["conversation_id"] = str(
        data.get("conversation_id")
        or data.get("subagent_conversation_id")
        or data.get("session_id")
        or data.get("CURSOR_CONVERSATION_ID")
        or ""
    )
    roots = data.get("workspace_roots") or data.get("workspaceRoots") or []
    if isinstance(roots, list) and roots:
        out["project_dir"] = str(roots[0])
    for key in ("cwd", "workspace_root", "project_dir", "CURSOR_PROJECT_DIR"):
        if data.get(key):
            out["project_dir"] = str(data[key])
            break
print(json.dumps(out))
PY
)"
  CHILD_CONV="$(printf '%s\n' "$CHILD_META" | python3 -c "import sys,json; print(json.load(sys.stdin).get('conversation_id',''))" 2>/dev/null || true)"
  CHILD_REPO="$(printf '%s\n' "$CHILD_META" | python3 -c "import sys,json; print(json.load(sys.stdin).get('project_dir',''))" 2>/dev/null || true)"
  [ -n "$CHILD_CONV" ] && export CURSOR_CONVERSATION_ID="$CHILD_CONV"
  [ -n "$CHILD_REPO" ] && export CURSOR_PROJECT_DIR="$CHILD_REPO"
  "$HOOK_DIR/graphiti-prefetch.sh" >/dev/null 2>&1 || true
fi

# PYTHONPATH (not cd): the module must import from the governance root while
# the hook's working directory stays the host workspace — it is one of the
# fail-closed resolution roots for the root Autonomy runtime database.
printf '%s\n' "$INPUT" | PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  "$PY" -m environment.agents.lifecycle.compose_start --mode "$MODE"
