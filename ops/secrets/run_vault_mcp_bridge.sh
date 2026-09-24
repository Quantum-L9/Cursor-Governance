#!/usr/bin/env bash
# Spawn wrapper for a vault-bound MCP bridge (ops/secrets/vault_mcp_bridge.py).
#
# .mcp.json launches this with the bridge name. The bridge binds the remote
# server's credential from Infisical in-process — as this surface's machine
# identity — so the key is never in the environment, argv, or a file. The
# locked governance interpreter is used (capability_bind reads the inventory
# with PyYAML). stdout is the MCP channel; this script prints nothing to it.
set -euo pipefail

GOV="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
if [[ -x "$GOV/.venv/bin/python3" ]]; then
  PY="$GOV/.venv/bin/python3"
elif [[ -x "$GOV/.venv/bin/python" ]]; then
  PY="$GOV/.venv/bin/python"
else
  echo "run_vault_mcp_bridge: governance interpreter missing at $GOV/.venv — refuse to launch" >&2
  exit 1
fi
exec "$PY" "$GOV/ops/secrets/vault_mcp_bridge.py" "$@"
