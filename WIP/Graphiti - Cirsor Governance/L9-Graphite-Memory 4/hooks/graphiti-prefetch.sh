#!/usr/bin/env bash
# Graphiti prefetch — used by orchestrator; can run standalone
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
# shellcheck source=graphiti_common.sh
source "$(dirname "$REAL_HOOK")/graphiti_common.sh"
graphiti_enabled || exit 0
graphiti_resolve_cli
graphiti_scaffold_memory_bank "${CURSOR_PROJECT_DIR:-}"
export CURSOR_CONVERSATION_ID="${CURSOR_CONVERSATION_ID:-default}"
python3 "$GRAPHITI_CLI" inject "${1:-session start}" >/dev/null 2>&1 || true
exit 0
