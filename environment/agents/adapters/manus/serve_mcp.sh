#!/usr/bin/env bash
# Launch the Manus streamable-HTTP MCP adapter with the governance locked Python.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_GOVERNANCE="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
GOVERNANCE="$DEFAULT_GOVERNANCE"

if [ "${1:-}" = "--governance" ]; then
  GOVERNANCE="${2:?--governance needs a path}"
  shift 2
fi
GOVERNANCE="$(cd "$GOVERNANCE" && pwd -P)"
PYTHON="$GOVERNANCE/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  printf 'manus-mcp ERROR: locked interpreter missing at %s; run make venv first\n' "$PYTHON" >&2
  exit 1
fi
if [ ! -f "$GOVERNANCE/CANONICAL_LAW.md" ]; then
  printf 'manus-mcp ERROR: no governance SSOT at %s\n' "$GOVERNANCE" >&2
  exit 1
fi

# The lifecycle bridge is a pre-launch signed-agent handoff, exactly like the
# package-owned MCP server on peer surfaces. A server child cannot add this
# material to an already-running parent, so it must be resolved before exec.
# The helper exports only the Manus assertion/key/grant subset and never the
# human private entrance. An absent local map leaves lifecycle tools honestly
# blocked rather than silently using the local-operator fallback.
LIFECYCLE=0
LIFECYCLE_TOKEN=0
for arg in "$@"; do
  [ "$arg" = "--enable-memory-lifecycle" ] && LIFECYCLE=1
  [ "$arg" = "--auth-token-file" ] && LIFECYCLE_TOKEN=1
done
if [ "$LIFECYCLE" = "1" ]; then
  if [ "$LIFECYCLE_TOKEN" != "1" ]; then
    printf '%s\n' 'manus-mcp ERROR: --enable-memory-lifecycle requires --auth-token-file' >&2
    exit 2
  fi
  if [ -n "${L9_MEMORY_HUMAN_DOOR_SECRET:-}" ]; then
    printf '%s\n' 'manus-mcp ERROR: refusing human memory door in an agent service' >&2
    exit 1
  fi
  if [ -n "${L9_MEMORY_AGENT_ID:-}" ] && [ "$L9_MEMORY_AGENT_ID" != "manus" ]; then
    printf '%s\n' 'manus-mcp ERROR: L9_MEMORY_AGENT_ID must be manus for lifecycle mode' >&2
    exit 1
  fi
  export L9_GOVERNANCE_DIR="$GOVERNANCE"
  export L9_MEMORY_AGENT_ID=manus
  export USER_ID=manus_agent
  export L9_MEMORY_SOURCE=manus
  # shellcheck source=/dev/null
  source "$GOVERNANCE/ops/memory/export_agent_assertion_env.sh"
fi

exec "$PYTHON" "$SCRIPT_DIR/mcp_server.py" --governance-root "$GOVERNANCE" "$@"
