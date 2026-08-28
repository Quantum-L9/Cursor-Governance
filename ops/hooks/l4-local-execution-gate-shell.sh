#!/usr/bin/env bash
# beforeShellExecution — one resolver, one gate, fail closed.
# Resolution SSOT: ops/autonomy/resolve_execution_gate.py
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
RESOLVER=""
if [[ -f "$HOOK_DIR/../autonomy/resolve_execution_gate.py" ]]; then
  RESOLVER="$HOOK_DIR/../autonomy/resolve_execution_gate.py"
elif [[ -f "${HOME}/.cursor-governance/ops/autonomy/resolve_execution_gate.py" ]]; then
  RESOLVER="${HOME}/.cursor-governance/ops/autonomy/resolve_execution_gate.py"
fi

_deny_internal() {
  printf '%s\n' '{"permission":"deny","user_message":"INTERNAL_EVALUATION_ERROR: the execution gate could not complete a policy evaluation for this command, so it denied it. This is a gate fault, not a policy decision about the command."}'
  exit 0
}

INPUT="$(cat)"
if [[ -z "$RESOLVER" || ! -f "$RESOLVER" ]]; then
  echo "l4-local-execution-gate-shell: resolver missing; failing closed" >&2
  _deny_internal
fi

GATE="$(python3 "$RESOLVER" --hook "$REAL_HOOK" --event-json - <<<"$INPUT")" || _deny_internal
if [[ -z "${GATE:-}" || ! -f "$GATE" ]]; then
  echo "l4-local-execution-gate-shell: gate unresolved; failing closed" >&2
  _deny_internal
fi

# stderr stays visible — swallowing it hid the last remediator deny.
if ! OUT="$(python3 "$GATE" cursor-shell <<<"$INPUT")"; then
  echo "l4-local-execution-gate-shell: gate exited non-zero; failing closed" >&2
  _deny_internal
fi
if [[ -z "$OUT" ]]; then
  echo "l4-local-execution-gate-shell: gate returned empty stdout; failing closed" >&2
  _deny_internal
fi
printf '%s\n' "$OUT"
exit 0
