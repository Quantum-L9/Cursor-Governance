#!/usr/bin/env bash
# /wire governance — repair repo symlinks + sessionEnd hook, then re-check.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"

WORKSPACE="${1:-$(pwd)}"

resolve_governance_paths_or_exit

echo "=== /wire governance — repairing workspace wiring ==="
echo "  Workspace: $WORKSPACE"
echo ""

(
  cd "$WORKSPACE"
  bash "$GLOBAL_COMMANDS/ops/scripts/setup_workspace_symlinks.sh"
)

echo ""
bash "$SCRIPT_DIR/check_governance_wiring.sh" "$WORKSPACE"
