#!/usr/bin/env bash
# Native Cursor subagentStop: preserve the real host payload before result validation.
set -uo pipefail
set +x
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
if [ -x "$ROOT/.venv/bin/python3" ]; then PY="$ROOT/.venv/bin/python3"; else PY="$(command -v python3)"; fi
INPUT="$(cat)"
REPORT="$(printf '%s\n' "$INPUT" | PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  "$PY" -m environment.agents.lifecycle.compose_stop)"
RC=$?
printf '%s\n' "$REPORT"
# Governed close for the child conversation. The native subagentStop payload
# carries no conversation id, so derive the same child identity start stamped
# (ops/hooks/child_conversation.py) — otherwise the close lands on the parent
# and the child's prefetch receipt is never closed.
CHILD_META="$(INPUT="$INPUT" "$PY" "$HOOK_DIR/child_conversation.py" 2>/dev/null || true)"
CHILD_CONV="$(printf '%s\n' "$CHILD_META" | "$PY" -c "import sys,json; print(json.load(sys.stdin).get('conversation_id',''))" 2>/dev/null || true)"
CHILD_REPO="$(printf '%s\n' "$CHILD_META" | "$PY" -c "import sys,json; print(json.load(sys.stdin).get('project_dir',''))" 2>/dev/null || true)"
[ -n "$CHILD_CONV" ] && export CURSOR_CONVERSATION_ID="$CHILD_CONV"
[ -n "$CHILD_REPO" ] && export CURSOR_PROJECT_DIR="$CHILD_REPO"
# Fail-open: compose_stop stdout is the host contract and must not be mixed
# with close chatter.
printf '%s\n' "$INPUT" | "$HOOK_DIR/graphiti-session-end.sh" >/dev/null 2>&1 || true
if [ "$RC" -ne 0 ]; then
  echo "ERROR: native subagent stop evidence was captured but acceptance/ingress did not converge; inspect lifecycle receipts" >&2
  exit "$RC"
fi
exit 0
