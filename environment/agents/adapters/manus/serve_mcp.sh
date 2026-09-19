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

exec "$PYTHON" "$SCRIPT_DIR/mcp_server.py" --governance-root "$GOVERNANCE" "$@"
