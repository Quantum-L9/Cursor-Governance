#!/usr/bin/env bash
# Memory gate E2E (minimal) — deny/allow via a forced canonical session state
# file (ops/memory/session_state.py; stage C8). No provider, no MCP required.
set -euo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
GC_ROOT="$(cd "$(dirname "$REAL_HOOK")/.." && pwd)"
GATE_LIB="$GC_ROOT/graphiti/graphiti_gate_lib.py"
REPO_ROOT="$(cd "$GC_ROOT/.." && pwd)"
if [ -x "$REPO_ROOT/.venv/bin/python3" ]; then
  GATE_PYTHON="$REPO_ROOT/.venv/bin/python3"
else
  GATE_PYTHON="$(command -v python3)"
fi
STATE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/l9-memory-gate-e2e.XXXXXX")"
trap 'rm -rf "$STATE_DIR"' EXIT
export L9_MEMORY_SESSION_STATE_DIR="$STATE_DIR"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export L9_MEMORY_WRITE_GATES=1
TEST_STATE="$STATE_DIR/e2e-test.json"
GATE_IN='{"conversation_id":"e2e-test","tool_name":"Write"}'

# Stale hydration, nothing satisfied — expect deny
cat > "$TEST_STATE" <<'JSON'
{"schema":"cursor.memory-session-state/v1","authority":"none","session_id":"e2e-test","task_signature":"abc123","satisfied_task_signatures":[],"memory_status":"OK","timestamp":"2000-01-01T00:00:00+00:00"}
JSON
RESULT="$("$GATE_PYTHON" "$GATE_LIB" pre_tool_use <<< "$GATE_IN")"
echo "$RESULT" | grep -q '"deny"' || { echo "FAIL: expected deny"; exit 1; }

# Task explicitly satisfied — expect allow
cat > "$TEST_STATE" <<'JSON'
{"schema":"cursor.memory-session-state/v1","authority":"none","session_id":"e2e-test","task_signature":"abc123","satisfied_task_signatures":["abc123"],"memory_status":"OK","timestamp":"2000-01-01T00:00:00+00:00"}
JSON
RESULT="$("$GATE_PYTHON" "$GATE_LIB" pre_tool_use <<< "$GATE_IN")"
echo "$RESULT" | grep -q '"allow"' || { echo "FAIL: expected allow"; exit 1; }

echo "OK: memory gate E2E passed"
exit 0
