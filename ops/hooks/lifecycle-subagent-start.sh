#!/usr/bin/env bash
# Native Cursor subagent lifecycle bridge. Host hook JSON arrives on stdin.
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
HOOK_DIR="$(dirname "$REAL_HOOK")"
ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
MODE="${1:-subagent_start}"
INPUT="$(cat)"
if [ -x "$ROOT/.venv/bin/python3" ]; then PY="$ROOT/.venv/bin/python3"; else PY="$(command -v python3)"; fi

if [ "$MODE" = "subagent_start" ]; then
  # Preserve the existing Graphiti subagent gate, but feed it the same host JSON
  # instead of consuming stdin before the lifecycle bridge can see it.
  if ! printf '%s\n' "$INPUT" | "$HOOK_DIR/graphiti_gate_runner.sh" subagent >/dev/null; then
    printf '%s\n' '{"permission":"deny","reason":"Graphiti subagent gate failed"}'
    exit 1
  fi
fi

# PYTHONPATH (not cd): the module must import from the governance root while
# the hook's working directory stays the host workspace — it is one of the
# fail-closed resolution roots for the root Autonomy runtime database.
printf '%s\n' "$INPUT" | PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  "$PY" -m environment.agents.lifecycle.compose_start --mode "$MODE"
