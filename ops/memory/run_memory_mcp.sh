#!/usr/bin/env bash
# Spawn wrapper for Claude Code's l9-graphite-memory stdio server.
#
# Claude Code expands ${HOME} in the projected .mcp.json, then launches this
# script. The wrapper bind-proves the interpreter so a Dock-started desktop
# session does not need L9_MEMORY_INTERPRETER in the parent environment.
# Resolution stays in ops.memory.runtime_binding (one brain). Fail closed:
# an unbound interpreter never execs a guess.
#
# No credentials. No env block. Extra argv from .mcp.json is forwarded.
set -euo pipefail

GOV="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
BIND="$GOV/ops/scripts/lib/bind_memory_interpreter.sh"

if [[ ! -f "$GOV/CANONICAL_LAW.md" || ! -f "$BIND" ]]; then
  echo "run_memory_mcp: governance clone missing at $GOV" >&2
  exit 1
fi

if [[ -x "$GOV/.venv/bin/python3" ]]; then
  PY="$GOV/.venv/bin/python3"
elif [[ -x "$GOV/.venv/bin/python" ]]; then
  PY="$GOV/.venv/bin/python"
else
  PY="$(command -v python3 || true)"
fi

if [[ -z "${PY:-}" || ! -x "$PY" ]]; then
  echo "run_memory_mcp: no python to prove the memory interpreter" >&2
  exit 1
fi

# shellcheck source=/dev/null
. "$BIND"
bind_l9_memory_interpreter "$PY" "$GOV"

if [[ -z "${L9_MEMORY_INTERPRETER:-}" || ! -x "$L9_MEMORY_INTERPRETER" ]]; then
  echo "run_memory_mcp: L9_MEMORY_INTERPRETER unbound — refuse to launch" >&2
  exit 1
fi

if [[ $# -gt 0 ]]; then
  exec "$L9_MEMORY_INTERPRETER" "$@"
fi
exec "$L9_MEMORY_INTERPRETER" -m l9_graphite_memory.server --transport stdio
