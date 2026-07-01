#!/usr/bin/env bash
# Cursor preToolUse hook — gate high-impact PlasticOS edits without Phase 0 evidence.
# Fail-open on hook errors. PlasticOS workspaces only.
set -uo pipefail

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
RESOLVE="$(dirname "$REAL_HOOK")/../scripts/resolve_governance_paths.sh"
# shellcheck source=../scripts/resolve_governance_paths.sh
source "$RESOLVE" 2>/dev/null || true

GATE_LIB=""
if resolve_governance_paths 2>/dev/null; then
  GATE_LIB="$GLOBAL_COMMANDS/skills/l9-code-graph-rag-mcp/scripts/code_graph_plasticos_gate.py"
else
  GATE_LIB="$HOME/.cursor-governance/skills/l9-code-graph-rag-mcp/scripts/code_graph_plasticos_gate.py"
fi

INPUT="$(cat)"
if [ ! -f "$GATE_LIB" ]; then
  echo '{"permission":"allow"}'
  exit 0
fi

python3 "$GATE_LIB" pre_tool_use "$INPUT" 2>/dev/null || echo '{"permission":"allow"}'
exit 0
