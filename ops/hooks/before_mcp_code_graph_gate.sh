#!/usr/bin/env bash
# Cursor beforeMCPExecution hook — deny chat indexing / get_graph on PlasticOS.
# Fail-open on hook errors.
set -uo pipefail

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
RESOLVE="$(dirname "$REAL_HOOK")/../scripts/resolve_governance_paths.sh"
# shellcheck source=../scripts/resolve_governance_paths.sh
source "$RESOLVE" 2>/dev/null || true

GATE_LIB=""
if resolve_governance_paths 2>/dev/null; then
  GATE_LIB="$GLOBAL_COMMANDS/skills/l9-code-graph-rag-mcp/scripts/code_graph_plasticos_gate.py"
else
  GATE_LIB="$HOME/Dropbox/Cursor Governance/GlobalCommands/skills/l9-code-graph-rag-mcp/scripts/code_graph_plasticos_gate.py"
fi

INPUT="$(cat)"
if [ ! -f "$GATE_LIB" ]; then
  echo '{"permission":"allow"}'
  exit 0
fi

python3 "$GATE_LIB" before_mcp "$INPUT" 2>/dev/null || echo '{"permission":"allow"}'
exit 0
