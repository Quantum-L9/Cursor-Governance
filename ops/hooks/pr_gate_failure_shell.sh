#!/usr/bin/env bash
# afterShellExecution — inject STOP LOOPING + named pytest nodes after make pr fails.
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
HELPER=""
if [[ -f "$HOOK_DIR/../scripts/pr_gate_failure.py" ]]; then
  HELPER="$HOOK_DIR/../scripts/pr_gate_failure.py"
elif [[ -f "${HOME}/.cursor-governance/ops/scripts/pr_gate_failure.py" ]]; then
  HELPER="${HOME}/.cursor-governance/ops/scripts/pr_gate_failure.py"
fi
INPUT="$(cat)"
if [[ -z "$HELPER" || ! -f "$HELPER" ]]; then
  echo '{}'
  exit 0
fi
if OUT="$(python3 "$HELPER" after-shell <<< "$INPUT" 2>/dev/null)"; then
  echo "$OUT"
  exit 0
fi
echo '{}'
exit 0
