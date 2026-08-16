# Append one event to L9_PR_GATE_TRACE when that path is set.
# Used to prove the make pr DAG executes resolve + pre-commit once per state.
# shellcheck shell=bash

pr_gate_trace() {
  local event="${1:-}"
  if [[ -z "$event" || -z "${L9_PR_GATE_TRACE:-}" ]]; then
    return 0
  fi
  printf '%s\n' "$event" >>"$L9_PR_GATE_TRACE"
}
