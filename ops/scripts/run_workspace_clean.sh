#!/usr/bin/env bash
# make clean / make workspace-clean — ship leftover work to scoped PRs, prune
# merged locals, prime a clean main worktree. Never broad-add or force-push.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WS="${WS:-$(pwd)}"
WS="$(cd "$WS" && pwd)"
CLEAN_MODE="${CLEAN_MODE:-apply}"
CLEAN_REMOTE="${CLEAN_REMOTE:-1}"
PR_BASE="${PR_BASE:-origin/main}"

if [[ -x "$GOV_ROOT/.venv/bin/python" ]]; then
  PY="$GOV_ROOT/.venv/bin/python"
else
  PY="python3"
fi

args=(
  --workspace "$WS"
  --gov-root "$GOV_ROOT"
  --baseline "$PR_BASE"
  --mode "$CLEAN_MODE"
)
if [[ "$CLEAN_REMOTE" = "1" && "$CLEAN_MODE" = "apply" ]]; then
  args+=(--remote)
fi

exec "$PY" "$GOV_ROOT/ops/scripts/workspace_clean.py" "${args[@]}"
