#!/usr/bin/env bash
# beforeShellExecution — deny make campaign / run_campaign.py when a latched plan fails kernel_pass.
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
GATE="$HOOK_DIR/plan_kernel_gate.py"
if [[ ! -f "$GATE" ]]; then
  echo '{"permission":"allow"}'
  exit 0
fi
if OUT="$(python3 "$GATE" --execute-gate 2>/dev/null)"; then
  echo "$OUT"
  exit 0
fi
echo '{"permission":"allow"}'
exit 0
