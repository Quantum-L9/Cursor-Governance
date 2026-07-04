#!/usr/bin/env bash
# One-time per-MACHINE Graphiti setup — NOT per-repo. Safe to run after every clone (idempotent).
# Usage: bash .cursor-commands/ops/scripts/init_graphiti_machine_env.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"
resolve_governance_paths_or_exit

DEFAULTS="$GLOBAL_COMMANDS/ops/graphiti/graphiti.env.defaults"
EXAMPLE="$GLOBAL_COMMANDS/ops/graphiti/graphiti.env.example"
MACHINE_ENV="$HOME/.cursor/graphiti.env"
SECRETS_DIR="$HOME/.cursor/secrets"
SECRETS_ENV="$SECRETS_DIR/graphiti.env"
SECRETS_EXAMPLE="$SECRETS_DIR/graphiti.env.example"

echo "=== Graphiti machine env init (once per Mac, not per repo clone) ==="
echo ""

mkdir -p "$HOME/.cursor" "$SECRETS_DIR"

# 1. Machine env — create from example only if missing (never overwrite secrets)
if [ -f "$MACHINE_ENV" ]; then
  echo "OK: $MACHINE_ENV already exists (not overwritten)"
else
  if [ -f "$EXAMPLE" ]; then
    grep -v '^OPENAI_API_KEY=' "$EXAMPLE" | grep -v '^NEO4J_PASSWORD=' >"$MACHINE_ENV" || cp "$EXAMPLE" "$MACHINE_ENV"
    echo "CREATED: $MACHINE_ENV from example (VPS-only secrets stripped)"
  else
    cat >"$MACHINE_ENV" <<'EOF'
# Machine-level Graphiti config — configure once per Mac. Repo clones do NOT need this file.
GRAPHITI_MEMORY_ENABLED=1
GRAPHITI_WRITE_GATES=0
GRAPHITI_TUNNEL_AUTOSTART=1
EOF
    echo "CREATED: minimal $MACHINE_ENV"
  fi
fi

# 2. Source defaults into machine env if keys missing
if [ -f "$DEFAULTS" ]; then
  # shellcheck disable=SC1090
  set -a && source "$DEFAULTS" && set +a
fi

# 3. Secrets overlay template
if [ ! -f "$SECRETS_EXAMPLE" ]; then
  cat >"$SECRETS_EXAMPLE" <<'EOF'
# Optional secrets overlay — NEVER commit. Loaded after ~/.cursor/graphiti.env
# Alternative: store in macOS Keychain (recommended):
#   security add-generic-password -a "$USER" -s graphiti-mcp-token -w "YOUR_TOKEN"
GRAPHITI_MCP_TOKEN=
EOF
  echo "CREATED: $SECRETS_EXAMPLE"
fi

if [ ! -f "$SECRETS_ENV" ]; then
  echo "HINT: copy $SECRETS_EXAMPLE → $SECRETS_ENV and set GRAPHITI_MCP_TOKEN"
  echo "      OR: security add-generic-password -a \"\$USER\" -s graphiti-mcp-token -w \"TOKEN\""
fi

# 4. SSH key hint
SSH_KEY="${GRAPHITI_SSH_KEY:-$HOME/.ssh/Hetzner-C1-nopass}"
if [ ! -f "$SSH_KEY" ]; then
  echo "HINT: place C1 SSH key at $SSH_KEY (chmod 600)"
  echo "      OR: security add-generic-password -a \"\$USER\" -s graphiti-c1-ssh-key -w \"\$(cat key)\""
  echo "      OR: repo .env.local C1_SSH (gitignored) — extracted automatically by ensure_graphiti_tunnel.sh"
fi

# 5. Status
echo ""
python3 - <<PY
import json, sys
sys.path.insert(0, "$GLOBAL_COMMANDS/ops/graphiti")
from graphiti_env_loader import env_status
print(json.dumps(env_status(), indent=2))
PY

echo ""
echo "Next: bash .cursor-commands/ops/scripts/install_cursor_hooks_bootstrap.sh  # if hooks not installed"
echo "      python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health"
