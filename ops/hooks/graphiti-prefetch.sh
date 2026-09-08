#!/usr/bin/env bash
# Standalone canonical prefetch — used by the orchestrator; can run standalone.
# Compiles the session hydration packet through the memory control plane
# (ops/memory) and writes the local session state; never calls a provider.
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
# shellcheck source=graphiti_common.sh
source "$HOOK_DIR/graphiti_common.sh"
graphiti_enabled || exit 0
ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
[ -f "$ROOT/ops/graphiti/hydration/cli.py" ] || ROOT="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
if [ -x "$ROOT/.venv/bin/python3" ]; then PY="$ROOT/.venv/bin/python3"; else PY="$(command -v python3)"; fi
export CURSOR_CONVERSATION_ID="${CURSOR_CONVERSATION_ID:-default}"
REPO="${CURSOR_PROJECT_DIR:-$PWD}"
(cd "$ROOT" && PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  "$PY" -m ops.graphiti.hydration.cli compile \
  --project-dir "$REPO" --session-id "$CURSOR_CONVERSATION_ID" \
  --agent-id "${L9_MEMORY_AGENT_ID:-cursor}" --format json) >/dev/null 2>&1 || true
exit 0
