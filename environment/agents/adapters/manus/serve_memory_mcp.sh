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
MATERIALIZER="$SCRIPT_DIR/materialize_memory_authority.py"

if [ ! -x "$PYTHON" ] || [ ! -x "$MEMORY_SERVER" ]; then
  printf '%s\n' 'manus-memory-mcp ERROR: pinned l9-graphite-memory runtime is unavailable' >&2
  exit 1
fi
if [ ! -f "$GOVERNANCE/CANONICAL_LAW.md" ]; then
  printf 'manus-memory-mcp ERROR: no governance SSOT at %s\n' "$GOVERNANCE" >&2
  exit 1
fi
if [ ! -f "$MATERIALIZER" ]; then
  printf '%s\n' 'manus-memory-mcp ERROR: scoped authority materializer is unavailable' >&2
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

# A persistent connector may receive only the shared agent door and Manus's own
# signing key in its encrypted connector environment. Never accept the human
# door, peer-agent keys, a provider URL, or a pre-minted assertion. The helper
# derives the public Manus grant from the canonical registry and writes both
# maps below a unique 0700 runtime directory for this child process only.
RUNTIME_PARENT="${XDG_RUNTIME_DIR:-/tmp}"
if [ ! -d "$RUNTIME_PARENT" ]; then
  RUNTIME_PARENT=/tmp
fi
umask 077
RUNTIME_AUTHORITY_DIRECTORY="$(mktemp -d "$RUNTIME_PARENT/l9-manus-memory.XXXXXX")"
chmod 700 "$RUNTIME_AUTHORITY_DIRECTORY"
cleanup() {
  rm -rf "$RUNTIME_AUTHORITY_DIRECTORY"
}
trap cleanup EXIT HUP INT TERM

if [ -n "${L9_MANUS_MEMORY_AUTHORITY_JSON:-}" ]; then
  printf '%s' "$L9_MANUS_MEMORY_AUTHORITY_JSON" \
    | "$PYTHON" "$MATERIALIZER" \
      --governance "$GOVERNANCE" \
      --output-directory "$RUNTIME_AUTHORITY_DIRECTORY"
  unset L9_MANUS_MEMORY_AUTHORITY_JSON
  export L9_MEMORY_SECRET_MAP="$RUNTIME_AUTHORITY_DIRECTORY/agent_tokens.local.json"
  export L9_MEMORY_GRANTS_MAP="$RUNTIME_AUTHORITY_DIRECTORY/agent_grants.json"
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

# Do not exec: the parent owns cleanup of the per-process authority directory.
set +e
"$MEMORY_SERVER" --transport stdio
server_status=$?
set -e
exit "$server_status"
