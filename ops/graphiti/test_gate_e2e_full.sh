#!/usr/bin/env bash
# Memory gate full E2E — pre_tool, shell, subagent, GMP, gates-off, against the
# canonical session state (ops/memory/session_state.py; stage C8). No provider,
# no MCP required: the state file is forced under a private state dir.
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
TEST_STATE="$STATE_DIR/e2e-test.json"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

run_gate() {
  local mode="$1"
  export L9_MEMORY_WRITE_GATES=1
  "$GATE_PYTHON" "$GATE_LIB" "$mode" <<< "$2"
}

write_state() {
  # $1 timestamp, $2 memory_status, $3 satisfied json list
  cat > "$TEST_STATE" <<JSON
{"schema":"cursor.memory-session-state/v1","authority":"none","session_id":"e2e-test","task_signature":"abc123","satisfied_task_signatures":$3,"memory_status":"$2","timestamp":"$1"}
JSON
}

expect() {
  local label="$1" result="$2" want="$3"
  echo "$result" | grep -q "\"$want\"" || {
    echo "FAIL: $label expected $want got $result"
    exit 1
  }
}

STALE="2000-01-01T00:00:00+00:00"
FRESH="$("$GATE_PYTHON" -c 'from datetime import UTC, datetime; print(datetime.now(UTC).isoformat())')"

# --- pre_tool_use deny/allow ---
write_state "$STALE" OK '[]'
expect "pre_tool deny (stale hydration)" "$(run_gate pre_tool_use '{"conversation_id":"e2e-test","tool_name":"Write"}')" deny
write_state "$FRESH" OK '[]'
expect "pre_tool allow (fresh hydration)" "$(run_gate pre_tool_use '{"conversation_id":"e2e-test","tool_name":"Write"}')" allow
write_state "$STALE" OK '["abc123"]'
expect "pre_tool allow (task explicitly satisfied)" "$(run_gate pre_tool_use '{"conversation_id":"e2e-test","tool_name":"Write"}')" allow
write_state "$FRESH" BINDING_FAILED '[]'
expect "pre_tool deny (memory did not answer)" "$(run_gate pre_tool_use '{"conversation_id":"e2e-test","tool_name":"Write"}')" deny

# --- GMP prompts are gated on hydration only (E7) ---
write_state "$FRESH" NO_HITS '[]'
expect "gmp allow on hydration alone" "$(run_gate pre_tool_use '{"conversation_id":"e2e-test","tool_name":"Write","prompt":"GMP Phase 0 TODO plan lock"}')" allow
write_state "$STALE" OK '[]'
expect "gmp deny without hydration" "$(run_gate pre_tool_use '{"conversation_id":"e2e-test","tool_name":"Write","prompt":"GMP Phase 0"}')" deny

# --- shell: git/gh exempt; make push gated ---
write_state "$STALE" OK '[]'
expect "shell git exempt without hydration" "$(run_gate shell '{"conversation_id":"e2e-test","command":"git commit -m x"}')" allow
expect "shell ls allow" "$(run_gate shell '{"conversation_id":"e2e-test","command":"ls -la"}')" allow
expect "shell make push deny" "$(run_gate shell '{"conversation_id":"e2e-test","command":"make push"}')" deny
write_state "$FRESH" OK '[]'
expect "shell make push allow when hydrated" "$(run_gate shell '{"conversation_id":"e2e-test","command":"make push"}')" allow

# --- subagent: inherits the PARENT's evidence, read-only ---
write_state "$STALE" OK '[]'
expect "subagent deny" "$(run_gate subagent '{"conversation_id":"e2e-test"}')" deny
expect "subagent deny via parent id" "$(run_gate subagent '{"parent_conversation_id":"e2e-test","conversation_id":"child"}')" deny
write_state "$FRESH" OK '[]'
expect "subagent allow via parent id" "$(run_gate subagent '{"parent_conversation_id":"e2e-test","conversation_id":"child"}')" allow
[ ! -f "$STATE_DIR/child.json" ] || { echo "FAIL: subagent gate must never write state"; exit 1; }

# --- gates off ---
export L9_MEMORY_WRITE_GATES=0
write_state "$STALE" OK '[]'
expect "gates off" "$("$GATE_PYTHON" "$GATE_LIB" pre_tool_use <<< '{"conversation_id":"e2e-test","tool_name":"Write"}')" allow

echo "OK: memory gate E2E full passed"
exit 0
