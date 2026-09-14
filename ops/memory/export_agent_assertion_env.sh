#!/usr/bin/env bash
# Export the ADR-0031 agent MCP assertion env for ONE principal into the
# CURRENT shell — the shell that is about to launch the host (Cursor, Claude
# Code) whose MCP server must inherit it. This is the pre-launch handoff: a
# SessionStart hook runs as a child of the host and cannot deliver env to the
# host or to the separately launched l9-graphite-memory server, so source this
# BEFORE starting the host.
#
# Exports only $AGENT_ID's signing key and grant entry (never a peer's, never
# the whole map). NEVER exports L9_MEMORY_HUMAN_DOOR_SECRET.
# Safe to `source`: missing maps return without exiting the caller.
set -uo pipefail
AGENT_ID="${L9_MEMORY_AGENT_ID:-cursor}"
SECRET_MAP="${L9_MEMORY_SECRET_MAP:-$HOME/.config/l9-memory/agent_tokens.local.json}"
GRANTS_MAP="${L9_MEMORY_GRANTS_MAP:-$HOME/.config/l9-memory/agent_grants.json}"
GOV_ROOT="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
# Prefer the bound memory interpreter; the helper's fallback mint uses the
# package wire format, so python3 without the package still mints a token the
# server verifies.
PY="${L9_MEMORY_INTERPRETER:-python3}"
_sourced=0
if [[ "${BASH_SOURCE[0]-}" != "${0:-}" ]]; then
  _sourced=1
fi
_done() {
  if [[ "$_sourced" -eq 1 ]]; then
    return "$1"
  fi
  exit "$1"
}
if [[ ! -f "$SECRET_MAP" || ! -f "$GRANTS_MAP" ]]; then
  echo "assertion env skipped: secret/grants map missing (memory-blind OK)" >&2
  _done 0
fi
# The helper refuses a terminal stdout; the command substitution below is a
# pipe, and eval is the only consumer of the export lines.
# shellcheck disable=SC1090
eval "$(
  PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$GOV_ROOT" \
  "$PY" "$GOV_ROOT/ops/memory/print_agent_assertion_env.py" \
    --agent-id "$AGENT_ID" \
    --secret-map "$SECRET_MAP" \
    --grants-map "$GRANTS_MAP" \
    --format shell
)" || true
_done 0
