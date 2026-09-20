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
  CHILD_META="$(INPUT="$INPUT" "$PY" "$HOOK_DIR/child_conversation.py")"
  CHILD_CONV="$(printf '%s\n' "$CHILD_META" | "$PY" -c "import sys,json; print(json.load(sys.stdin).get('conversation_id',''))" 2>/dev/null || true)"
  CHILD_REPO="$(printf '%s\n' "$CHILD_META" | "$PY" -c "import sys,json; print(json.load(sys.stdin).get('project_dir',''))" 2>/dev/null || true)"
  [ -n "$CHILD_CONV" ] && export CURSOR_CONVERSATION_ID="$CHILD_CONV"
  [ -n "$CHILD_REPO" ] && export CURSOR_PROJECT_DIR="$CHILD_REPO"
  "$HOOK_DIR/graphiti-prefetch.sh" >/dev/null 2>&1 || true
fi

# PYTHONPATH (not cd): the module must import from the governance root while
# the hook's working directory stays the host workspace — it is one of the
# fail-closed resolution roots for the root Autonomy runtime database.
printf '%s\n' "$INPUT" | PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  "$PY" -m environment.agents.lifecycle.compose_start --mode "$MODE"
