#!/usr/bin/env bash
# Launch the package-owned signed Manus memory MCP lane over stdio.
#
# This is deliberately not an HTTP proxy and contains no memory business logic.
# Manus starts this command as a stdio Custom MCP connector; the exact pinned
# l9-graphite-memory MCP server owns tool discovery, authorization, and writes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_GOVERNANCE="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
GOVERNANCE="$DEFAULT_GOVERNANCE"

if [ "${1:-}" = "--governance" ]; then
  GOVERNANCE="${2:?--governance needs a path}"
  shift 2
fi
if [ "$#" -ne 0 ]; then
  printf '%s\n' "manus-memory-mcp ERROR: unexpected argument: $1" >&2
  exit 2
fi
GOVERNANCE="$(cd "$GOVERNANCE" && pwd -P)"
PYTHON="$GOVERNANCE/.venv/bin/python"
MEMORY_SERVER="$GOVERNANCE/.venv/bin/l9-memory-server"

if [ ! -x "$PYTHON" ] || [ ! -x "$MEMORY_SERVER" ]; then
  printf '%s\n' 'manus-memory-mcp ERROR: pinned l9-graphite-memory runtime is unavailable' >&2
  exit 1
fi
if [ ! -f "$GOVERNANCE/CANONICAL_LAW.md" ]; then
  printf 'manus-memory-mcp ERROR: no governance SSOT at %s\n' "$GOVERNANCE" >&2
  exit 1
fi
if [ -n "${L9_MEMORY_HUMAN_DOOR_SECRET:-}" ]; then
  printf '%s\n' 'manus-memory-mcp ERROR: refusing human memory door in an agent process' >&2
  exit 1
fi
if [ -n "${L9_MEMORY_AGENT_ID:-}" ] && [ "$L9_MEMORY_AGENT_ID" != "manus" ]; then
  printf '%s\n' 'manus-memory-mcp ERROR: L9_MEMORY_AGENT_ID must be manus' >&2
  exit 1
fi

# The helper writes a short-lived 0600 source file, exports only Manus's scoped
# assertion/key/grant subset into this server process, and never exports the
# human private door. A connector child cannot recover safely from a missing
# pre-launch handoff, so fail before the package server could select its
# local-operator compatibility principal.
export L9_GOVERNANCE_DIR="$GOVERNANCE"
export L9_MEMORY_AGENT_ID=manus
export USER_ID=manus_agent
export L9_MEMORY_SOURCE=manus
# shellcheck source=/dev/null
source "$GOVERNANCE/ops/memory/export_agent_assertion_env.sh"

missing=()
for name in \
  L9_MEMORY_AGENTS_DOOR_SECRET \
  L9_MEMORY_AGENT_ASSERTION \
  L9_MEMORY_AGENT_SIGNING_KEYS_JSON \
  L9_MEMORY_AGENT_GRANTS_JSON; do
  [ -n "${!name:-}" ] || missing+=("$name")
done
if [ "${#missing[@]}" -ne 0 ]; then
  printf '%s\n' "manus-memory-mcp ERROR: signed Manus memory door unavailable; missing ${missing[*]}" >&2
  exit 1
fi

exec "$MEMORY_SERVER" --transport stdio
