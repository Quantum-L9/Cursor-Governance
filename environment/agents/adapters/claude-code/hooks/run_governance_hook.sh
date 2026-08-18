#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# One interpreter contract for every governance-owned Claude Code Python hook.
#
# Each hook command used to end in `exec python3 "$f"`, which is a PATH lookup:
# whatever interpreter happens to be first wins. On a container whose system
# python3 lacks the locked dependencies, a hook still exits 0 while never
# reaching its implementation — memory write-back "succeeded" for every session
# without ever writing a PICKUP episode (F-13).
#
# Resolution order is the same one session_start_claude_governance.sh and
# ops/scripts/bootstrap_agent_environment.sh already use:
#
#     $HOME/.cursor-governance/.venv/bin/python3
#     $HOME/.cursor-governance/.venv/bin/python
#
# $HOME/.cursor-governance is the sole governance root (rule 06); the hook
# commands in settings.template.json already address every script through it.
#
# There is deliberately NO fallback to system python3. A governance hook that
# needs locked dependencies and cannot get them has not run, and saying so on
# stderr is the honest outcome — silently running it on the wrong interpreter is
# the defect this script exists to remove.
#
# Exit semantics follow the contract the hook commands already had: a missing
# governance clone exits 0 rather than blocking the session. A missing locked
# interpreter is reported the same way, loudly, on stderr.
#
# Usage (from settings.template.json):
#   run_governance_hook.sh <hook-basename.py> [args...]
# ---------------------------------------------------------------------------
set -uo pipefail

HOOK_NAME="${1:-}"
if [ -z "$HOOK_NAME" ]; then
  printf 'l9-hook: usage: run_governance_hook.sh <hook.py> [args...]\n' >&2
  exit 0
fi
shift

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$HOOK_DIR/$HOOK_NAME"
[ -f "$HOOK" ] || exit 0

GOV="$HOME/.cursor-governance"
GOV_PY=""
for candidate in "$GOV/.venv/bin/python3" "$GOV/.venv/bin/python"; do
  if [ -x "$candidate" ]; then
    GOV_PY="$candidate"
    break
  fi
done

if [ -z "$GOV_PY" ]; then
  printf 'l9-hook: locked governance interpreter not found under %s/.venv — %s did NOT run.\n' \
    "$GOV" "$HOOK_NAME" >&2
  printf 'l9-hook: restore it with: make -C "%s" venv\n' "$GOV" >&2
  exit 0
fi

exec "$GOV_PY" "$HOOK" "$@"
