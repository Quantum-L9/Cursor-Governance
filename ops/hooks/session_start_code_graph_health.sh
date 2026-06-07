#!/usr/bin/env bash
# Cursor sessionStart hook — prefetch code-graph health for PlasticOS workspaces.
# Fail-open: never block session start. Uses CURSOR_PROJECT_DIR from hook runtime.
set -uo pipefail

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
RESOLVE="$(dirname "$REAL_HOOK")/../scripts/resolve_governance_paths.sh"
# shellcheck source=../scripts/resolve_governance_paths.sh
source "$RESOLVE" 2>/dev/null || true

REPO="${CURSOR_PROJECT_DIR:-}"
GOV_SKILLS=""
HEALTH_SCRIPT=""
SUMMARY="code-graph: skipped (no PlasticOS workspace)"
HEALTHY="0"
TOTALS=""

if [ -n "$REPO" ] && [ -d "$REPO/plasticos_base" ]; then
  if resolve_governance_paths 2>/dev/null; then
    GOV_SKILLS="$GLOBAL_COMMANDS/skills/l9-code-graph-rag-mcp/scripts"
  else
    GOV_SKILLS="$HOME/Dropbox/Cursor Governance/GlobalCommands/skills/l9-code-graph-rag-mcp/scripts"
  fi
  HEALTH_SCRIPT="$GOV_SKILLS/code_graph_health.sh"

  if [ -f "$HEALTH_SCRIPT" ]; then
    if OUT="$(bash "$HEALTH_SCRIPT" "$REPO" 2>/dev/null)"; then
      HEALTHY="1"
      TOTALS="$(echo "$OUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
t = d.get('data', {}).get('totals', {})
print(f\"entities={t.get('entities', 0)} relationships={t.get('relationships', 0)} files={t.get('files', 0)}\")
" 2>/dev/null || echo "healthy")"
      SUMMARY="code-graph: healthy (${TOTALS}). Grep first; read graph for importers/impact/cross-module only. Trigger matrix: skills/l9-code-graph-rag-mcp/assets/plasticos-trigger-matrix.md. Rule 87-plasticos-code-graph-rag; skill l9-code-graph-rag-mcp. GMP Phase 0: code_graph_gmp_baseline.sh."
    else
      SUMMARY="code-graph: UNHEALTHY — run in Terminal: bash ${GOV_SKILLS}/code_graph_batch_index.sh \"${REPO}\". Trigger matrix: skills/l9-code-graph-rag-mcp/assets/plasticos-trigger-matrix.md"
    fi
  fi
fi

export CODE_GRAPH_HEALTHY="$HEALTHY" CODE_GRAPH_REPO="$REPO" CODE_GRAPH_SUMMARY="$SUMMARY"
python3 - <<'PY'
import json
import os

print(
    json.dumps(
        {
            "env": {
                "CODE_GRAPH_HEALTHY": os.environ.get("CODE_GRAPH_HEALTHY", "0"),
                "CODE_GRAPH_REPO": os.environ.get("CODE_GRAPH_REPO", ""),
            },
            "additional_context": os.environ.get("CODE_GRAPH_SUMMARY", ""),
        }
    )
)
PY

exit 0
