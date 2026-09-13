#!/usr/bin/env bash
# Export ADR-0031 agent MCP assertion env for the current surface.
# NEVER exports L9_MEMORY_HUMAN_DOOR_SECRET.
set -euo pipefail
AGENT_ID="${L9_MEMORY_AGENT_ID:-cursor}"
SECRET_MAP="${L9_MEMORY_SECRET_MAP:-$HOME/.config/l9-memory/agent_tokens.local.json}"
GRANTS_MAP="${L9_MEMORY_GRANTS_MAP:-$HOME/.config/l9-memory/agent_grants.json}"
GOV_ROOT="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
PY="${L9_MEMORY_INTERPRETER:-python3}"
if [[ ! -f "$SECRET_MAP" || ! -f "$GRANTS_MAP" ]]; then
  echo "assertion env skipped: secret/grants map missing (memory-blind OK)" >&2
  exit 0
fi
# shellcheck disable=SC1090
eval "$(
  L9_MEMORY_AGENT_ID="$AGENT_ID" \
  L9_MEMORY_SECRET_MAP="$SECRET_MAP" \
  L9_MEMORY_GRANTS_MAP="$GRANTS_MAP" \
  PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$GOV_ROOT" \
  "$PY" "$GOV_ROOT/ops/memory/print_agent_assertion_env.py" \
    --agent-id "$AGENT_ID" \
    --secret-map "$SECRET_MAP" \
    --grants-map "$GRANTS_MAP" \
    --format shell
)"
