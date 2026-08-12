#!/usr/bin/env bash
# beforeShellExecution — L4 remote gate + shared-worktree isolation (scoop/revert/switch).
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
GATE=""
if [[ -f "$HOOK_DIR/../autonomy/local_execution_gate.py" ]]; then
  GATE="$HOOK_DIR/../autonomy/local_execution_gate.py"
elif [[ -f "${HOME}/.cursor-governance/ops/autonomy/local_execution_gate.py" ]]; then
  GATE="${HOME}/.cursor-governance/ops/autonomy/local_execution_gate.py"
fi
INPUT="$(cat)"
if [[ -z "$GATE" || ! -f "$GATE" ]]; then
  echo '{"permission":"allow"}'
  exit 0
fi
if OUT="$(python3 "$GATE" cursor-shell <<< "$INPUT" 2>/dev/null)"; then
  echo "$OUT"
  exit 0
fi
echo '{"permission":"allow"}'
exit 0
