#!/usr/bin/env bash
# Launch only the governance MCP adapter with the governance locked Python.
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
LIFECYCLE=0
LIFECYCLE_TOKEN=0
for arg in "$@"; do
  [ "$arg" = "--enable-memory-lifecycle" ] && LIFECYCLE=1
  [ "$arg" = "--auth-token-file" ] && LIFECYCLE_TOKEN=1
done
if [ "$LIFECYCLE" = "1" ] && [ "$LIFECYCLE_TOKEN" != "1" ]; then
  printf '%s\n' 'manus-mcp ERROR: --enable-memory-lifecycle requires --auth-token-file' >&2
  exit 2
fi
# Governance is not a Memory credential carrier. Strip every inherited Memory
# assertion/key/map and retired selector, including future legacy names.
# No mint/export helper is sourced, even when compatibility stubs are enabled.
for name in ${!L9_MEMORY_@}; do
  unset "$name"
done
unset L9_MANUS_MEMORY_AUTHORITY_JSON L9_ASSERTION_EXPORT_STATUS
exec "$PYTHON" "$SCRIPT_DIR/mcp_server.py" --governance-root "$GOVERNANCE" "$@"
