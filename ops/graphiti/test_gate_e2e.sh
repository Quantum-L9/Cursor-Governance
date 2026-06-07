#!/usr/bin/env bash
# GATES-002 E2E — verify gate deny/allow via forced state file (no MCP required)
set -euo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
GC_ROOT="$(cd "$(dirname "$REAL_HOOK")/.." && pwd)"
# shellcheck source=../hooks/graphiti_common.sh
source "$GC_ROOT/hooks/graphiti_common.sh"
graphiti_resolve_cli
GATE_LIB="$(dirname "$GRAPHITI_CLI")/graphiti_gate_lib.py"
STATE_DIR="$HOME/.cursor/graphiti-state"
mkdir -p "$STATE_DIR"
TEST_STATE="$STATE_DIR/e2e-test.json"
export GRAPHITI_WRITE_GATES=1

# Force empty satisfaction — expect deny
echo '{"conversation_id":"e2e-test","tool_name":"Write"}' > /tmp/gate_in.json
cat > "$TEST_STATE" <<'JSON'
{
  "group_id": "sandbox-test",
  "prefetch_ts": "2000-01-01T00:00:00Z",
  "task_signature": "abc123",
  "memory_satisfied_for": [],
  "cache_ttl_minutes": 30
}
JSON
RESULT="$(python3 "$GATE_LIB" pre_tool_use < /tmp/gate_in.json)"
echo "$RESULT" | grep -q '"deny"' || { echo "FAIL: expected deny"; exit 1; }

# Force satisfied — expect allow
cat > "$TEST_STATE" <<'JSON'
{
  "group_id": "sandbox-test",
  "prefetch_ts": "2099-01-01T00:00:00Z",
  "task_signature": "abc123",
  "memory_satisfied_for": ["abc123"],
  "cache_ttl_minutes": 30
}
JSON
RESULT="$(python3 "$GATE_LIB" pre_tool_use < /tmp/gate_in.json)"
echo "$RESULT" | grep -q '"allow"' || { echo "FAIL: expected allow"; exit 1; }

rm -f "$TEST_STATE"
echo "OK: graphiti gate E2E passed"
exit 0
