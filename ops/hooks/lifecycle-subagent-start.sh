#!/usr/bin/env bash
# Composed subagentStart: Graphiti gate then lifecycle DispatchReceipt.
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
# First: existing Graphiti subagent gate
if ! "$HOOK_DIR/graphiti_gate_runner.sh" subagent; then
  exit 1
fi
# Lifecycle composition is invoked when CURSOR_SUBAGENT_ASSIGNMENT_JSON is set.
# Without assignment payload, Graphiti-only behavior is preserved (compat).
if [ -n "${CURSOR_SUBAGENT_ASSIGNMENT_JSON:-}" ]; then
  ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
  if [ -x "$ROOT/.venv/bin/python3" ]; then PY="$ROOT/.venv/bin/python3"; else PY="$(command -v python3)"; fi
  echo "$CURSOR_SUBAGENT_ASSIGNMENT_JSON" | "$PY" -m environment.agents.lifecycle.compose_start
fi
exit 0
