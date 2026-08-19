#!/usr/bin/env bash
# GATES-002 full E2E — pre_tool, shell, subagent, GMP, gates-off
set -euo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
GC_ROOT="$(cd "$(dirname "$REAL_HOOK")/.." && pwd)"
# shellcheck source=../hooks/graphiti_common.sh
source "$GC_ROOT/hooks/graphiti_common.sh"
GATE_LIB="$GC_ROOT/graphiti/graphiti_gate_lib.py"
REPO_ROOT="$(cd "$GC_ROOT/.." && pwd)"
if [ -x "$REPO_ROOT/.venv/bin/python3" ]; then
  GRAPHITI_PYTHON="$REPO_ROOT/.venv/bin/python3"
else
  GRAPHITI_PYTHON="$(command -v python3)"
fi
STATE_DIR="$HOME/.cursor/graphiti-state"
mkdir -p "$STATE_DIR"
TEST_STATE="$STATE_DIR/e2e-test.json"
CONV='e2e-test'

run_gate() {
  local mode="$1"
  export GRAPHITI_WRITE_GATES=1
  "$GRAPHITI_PYTHON" "$GATE_LIB" "$mode" <<< "$2"
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

# --- GMP prompts are gated on hydration only (E7) ---
# A GMP-shaped prompt used to be denied until gmp:phase_lock appeared in
# memory_satisfied_for, which made a memory marker into repository-write
# permission. GMP freezes the authorized edit *scope*, not repository
# ownership, so a hydrated session may proceed without any lock.
cat > "$TEST_STATE" <<JSON
{"group_id":"sandbox-test","prefetch_ts":"2099-01-01T00:00:00Z","task_signature":"abc123","memory_satisfied_for":["abc123"],"cache_ttl_minutes":30}
JSON
expect "gmp allow on hydration alone" "$(run_gate pre_tool_use '{"conversation_id":"e2e-test","tool_name":"Write","prompt":"GMP Phase 0 TODO plan lock"}')" allow

# ...and the gate still enforces: no hydration, no write.
cat > "$TEST_STATE" <<JSON
{"group_id":"sandbox-test","prefetch_ts":"2000-01-01T00:00:00Z","task_signature":"abc123","memory_satisfied_for":[],"cache_ttl_minutes":30}
JSON
expect "gmp deny without hydration" "$(run_gate pre_tool_use '{"conversation_id":"e2e-test","tool_name":"Write","prompt":"GMP Phase 0"}')" deny

# --- shell ---
# git/gh execution is exempt from memory state by design: memory governs writes
# to the repository, not whether git may run (ops/autonomy/git_execution_exemption,
# landed with "Loosen git and gh execution governance"). This block previously
# expected an unhydrated `git commit` to be denied, an expectation the exemption
# had already made stale -- so the whole self-test failed and callers silently
# fell back to the minimal one. Assert the exemption instead.
cat > "$TEST_STATE" <<JSON
{"group_id":"sandbox-test","prefetch_ts":"2000-01-01T00:00:00Z","task_signature":"abc123","memory_satisfied_for":[],"cache_ttl_minutes":30}
JSON
expect "shell git exempt without hydration" "$(run_gate shell '{"conversation_id":"e2e-test","command":"git commit -m x"}')" allow
expect "shell ls allow" "$(run_gate shell '{"conversation_id":"e2e-test","command":"ls -la"}')" allow
expect "shell make push deny" "$(run_gate shell '{"conversation_id":"e2e-test","command":"make push"}')" deny

cat > "$TEST_STATE" <<JSON
{"group_id":"sandbox-test","prefetch_ts":"2099-01-01T00:00:00Z","task_signature":"abc123","memory_satisfied_for":["abc123"],"cache_ttl_minutes":30}
JSON
expect "shell make push allow when hydrated" "$(run_gate shell '{"conversation_id":"e2e-test","command":"make push"}')" allow

# --- subagent ---
cat > "$TEST_STATE" <<JSON
{"group_id":"sandbox-test","prefetch_ts":"2000-01-01T00:00:00Z","task_signature":"abc123","memory_satisfied_for":[],"cache_ttl_minutes":30}
JSON
expect "subagent deny" "$(run_gate subagent '{"conversation_id":"e2e-test"}')" deny

# --- gates off ---
export GRAPHITI_WRITE_GATES=0
expect "gates off" "$("$GRAPHITI_PYTHON" "$GATE_LIB" pre_tool_use <<< '{"conversation_id":"e2e-test","tool_name":"Write"}')" allow

rm -f "$TEST_STATE"
echo "OK: graphiti gate E2E full passed"
exit 0
