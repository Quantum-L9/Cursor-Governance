#!/usr/bin/env bash
# GATES-002 full E2E — pre_tool, shell, subagent, GMP, gates-off
set -euo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
GC_ROOT="$(cd "$(dirname "$REAL_HOOK")/.." && pwd)"
# shellcheck source=../hooks/graphiti_common.sh
source "$GC_ROOT/hooks/graphiti_common.sh"
GATE_LIB="$GC_ROOT/graphiti/graphiti_gate_lib.py"
STATE_DIR="$HOME/.cursor/graphiti-state"
mkdir -p "$STATE_DIR"
TEST_STATE="$STATE_DIR/e2e-test.json"
CONV='e2e-test'

run_gate() {
  local mode="$1"
  export GRAPHITI_WRITE_GATES=1
  python3 "$GATE_LIB" "$mode" <<< "$2"
}

expect() {
  local label="$1" result="$2" want="$3"
  echo "$result" | grep -q "\"$want\"" || {
    echo "FAIL: $label expected $want got $result"
    exit 1
  }
}

# --- pre_tool_use deny/allow ---
cat > "$TEST_STATE" <<JSON
{"group_id":"sandbox-test","prefetch_ts":"2000-01-01T00:00:00Z","task_signature":"abc123","memory_satisfied_for":[],"cache_ttl_minutes":30}
JSON
expect "pre_tool deny" "$(run_gate pre_tool_use '{"conversation_id":"e2e-test","tool_name":"Write"}')" deny

cat > "$TEST_STATE" <<JSON
{"group_id":"sandbox-test","prefetch_ts":"2099-01-01T00:00:00Z","task_signature":"abc123","memory_satisfied_for":["abc123"],"cache_ttl_minutes":30}
JSON
expect "pre_tool allow" "$(run_gate pre_tool_use '{"conversation_id":"e2e-test","tool_name":"Write"}')" allow

# --- GMP matcher ---
cat > "$TEST_STATE" <<JSON
{"group_id":"sandbox-test","prefetch_ts":"2099-01-01T00:00:00Z","task_signature":"abc123","memory_satisfied_for":["abc123"],"cache_ttl_minutes":30}
JSON
expect "gmp deny no lock" "$(run_gate pre_tool_use '{"conversation_id":"e2e-test","tool_name":"Write","prompt":"GMP Phase 0 TODO plan lock"}')" deny

cat > "$TEST_STATE" <<JSON
{"group_id":"sandbox-test","prefetch_ts":"2099-01-01T00:00:00Z","task_signature":"abc123","memory_satisfied_for":["abc123","gmp:phase_lock"],"cache_ttl_minutes":30}
JSON
expect "gmp allow with lock" "$(run_gate pre_tool_use '{"conversation_id":"e2e-test","tool_name":"Write","prompt":"GMP Phase 0"}')" allow

# --- shell ---
cat > "$TEST_STATE" <<JSON
{"group_id":"sandbox-test","prefetch_ts":"2000-01-01T00:00:00Z","task_signature":"abc123","memory_satisfied_for":[],"cache_ttl_minutes":30}
JSON
expect "shell commit deny" "$(run_gate shell '{"conversation_id":"e2e-test","command":"git commit -m x"}')" deny
expect "shell ls allow" "$(run_gate shell '{"conversation_id":"e2e-test","command":"ls -la"}')" allow

cat > "$TEST_STATE" <<JSON
{"group_id":"sandbox-test","prefetch_ts":"2099-01-01T00:00:00Z","task_signature":"abc123","memory_satisfied_for":["abc123"],"cache_ttl_minutes":30}
JSON
expect "shell commit allow" "$(run_gate shell '{"conversation_id":"e2e-test","command":"git commit -m x"}')" allow

# --- subagent ---
cat > "$TEST_STATE" <<JSON
{"group_id":"sandbox-test","prefetch_ts":"2000-01-01T00:00:00Z","task_signature":"abc123","memory_satisfied_for":[],"cache_ttl_minutes":30}
JSON
expect "subagent deny" "$(run_gate subagent '{"conversation_id":"e2e-test"}')" deny

# --- gates off ---
export GRAPHITI_WRITE_GATES=0
expect "gates off" "$(python3 "$GATE_LIB" pre_tool_use <<< '{"conversation_id":"e2e-test","tool_name":"Write"}')" allow

rm -f "$TEST_STATE"
echo "OK: graphiti gate E2E full passed"
exit 0
