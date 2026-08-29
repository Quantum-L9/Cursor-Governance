#!/usr/bin/env bash
# beforeShellExecution — one process: Graphiti + L4 + plan-kernel.
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
GATE="$(dirname "$REAL_HOOK")/before_shell_execution_gate.py"
_deny_internal() {
  printf '%s\n' '{"permission":"deny","user_message":"INTERNAL_EVALUATION_ERROR: the execution gate could not complete a policy evaluation for this command, so it denied it. This is a gate fault, not a policy decision about the command."}'
  exit 0
}

INPUT="$(cat)"
if [[ ! -f "$GATE" ]]; then
  echo "before-shell-execution-gate: python gate missing; failing closed" >&2
  _deny_internal
fi
if ! OUT="$(python3 "$GATE" <<<"$INPUT")"; then
  echo "before-shell-execution-gate: gate exited non-zero; failing closed" >&2
  _deny_internal
fi
if [[ -z "$OUT" ]]; then
  echo "before-shell-execution-gate: gate returned empty stdout; failing closed" >&2
  _deny_internal
fi
printf '%s\n' "$OUT"
exit 0
