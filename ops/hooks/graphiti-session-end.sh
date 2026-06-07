#!/usr/bin/env bash
# sessionEnd T0 — update memory-bank activeContext (no LLM)
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
# shellcheck source=graphiti_common.sh
source "$(dirname "$REAL_HOOK")/graphiti_common.sh"
REPO="${CURSOR_PROJECT_DIR:-}"
graphiti_enabled || exit 0
graphiti_scaffold_memory_bank "$REPO"
BANK="$REPO/memory-bank/activeContext.md"
[ -d "$(dirname "$BANK")" ] || exit 0
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
cat > "$BANK" <<EOF
# Where we left off (max ~1 screen)

**Last session:** $TS
**Repo:** $REPO
**Next action:** (update manually or via end-session command)

EOF
exit 0
