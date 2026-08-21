#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Claude Code hook launcher — the single place that decides what happens
# when a hook cannot run.
#
# Every L9 hook registration in the settings triad routes through this file so
# the fail-open / fail-closed decision is made ONCE, in reviewable shell, rather
# than being re-typed inside eight `bash -c '...'` one-liners where a copy-paste
# slip silently disables a gate.
#
# THE DISTINCTION THIS FILE EXISTS TO ENFORCE (INV-1):
#
#   --class gate      A hook that DECIDES whether a tool call may proceed.
#                     merge_gate_wrap, local_execution_gate_wrap, memory_gate.
#                     If it cannot evaluate — no launcher, no hook file, no
#                     locked interpreter — it exits 2 and the tool call is
#                     BLOCKED. A gate that cannot evaluate has not passed;
#                     it has failed to run, and those are not the same thing.
#
#   --class observer  A hook that RECORDS or ENRICHES but decides nothing.
#                     skill_usage_logger, user_prompt_skill_router,
#                     context7_stack_pretool, memory_prefetch, memory_writeback.
#                     If it cannot run it exits 0 — but it appends a timestamped
#                     line to ~/.l9/claude/hook-skips.log first, so the skip is
#                     auditable rather than invisible.
#
# The audit that produced this file found all eight hooks exiting 0 on a missing
# $GOV/.venv, printing one stderr line that nothing on Mobile surfaces. Three of
# those eight were gates. A memory gate, a merge gate and a publish-path gate
# that all fail open are indistinguishable from gates that passed (finding B-03).
#
# Exit codes are Claude Code's hook contract, not ours:
#   0  proceed
#   2  block the tool call and surface stderr to the model
#
# Usage (from settings.json):
#   l9_hook_exec.sh --class gate     merge_gate_wrap.py
#   l9_hook_exec.sh --class observer skill_usage_logger.py
# ---------------------------------------------------------------------------
set -uo pipefail

HOOK_CLASS=""
HOOK_NAME=""

while [ $# -gt 0 ]; do
  case "$1" in
    --class) HOOK_CLASS="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,40p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) HOOK_NAME="$1"; shift ;;
  esac
done

# A malformed registration must not be tolerated into a silent pass. We do not
# know whether the caller meant a gate, so we assume the stricter reading.
if [ -z "$HOOK_CLASS" ] || [ -z "$HOOK_NAME" ]; then
  printf 'l9-hook: malformed registration (class=%q name=%q) — refusing to guess\n' \
    "$HOOK_CLASS" "$HOOK_NAME" >&2
  exit 2
fi
case "$HOOK_CLASS" in
  gate|observer) : ;;
  *)
    printf 'l9-hook: unknown hook class %q (want gate|observer)\n' "$HOOK_CLASS" >&2
    exit 2
    ;;
esac

# The cloud SSOT is always $HOME/.cursor-governance. L9_GOVERNANCE_DIR is honoured
# only when it agrees, so an unexpanded literal '$HOME' from an .env-format
# environment field can never redirect a gate at its policy.
GOV_DIR="$HOME/.cursor-governance"
if [ -n "${L9_GOVERNANCE_DIR:-}" ] && [ "$L9_GOVERNANCE_DIR" != "$GOV_DIR" ]; then
  case "$L9_GOVERNANCE_DIR" in
    *'$HOME'*|*'${HOME}'*) : ;;
    *) [ -f "$L9_GOVERNANCE_DIR/CANONICAL_LAW.md" ] && GOV_DIR="$L9_GOVERNANCE_DIR" ;;
  esac
fi

SKIP_LOG="${L9_HOOK_SKIP_LOG:-$HOME/.l9/claude/hook-skips.log}"

# Every skip is timestamped in UTC. An undated skip log cannot answer the only
# question worth asking of it: was this hook skipped during the run I am
# investigating, or six weeks ago?
record_skip() {
  local reason="$1" ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 'unknown-time')"
  mkdir -p "$(dirname "$SKIP_LOG")" 2>/dev/null || return 0
  printf '%s observer %s %s\n' "$ts" "$HOOK_NAME" "$reason" >> "$SKIP_LOG" 2>/dev/null || true
}

# One exit path for "this hook cannot run", so a gate can never accidentally
# take the observer branch.
cannot_run() {
  local reason="$1"
  if [ "$HOOK_CLASS" = "gate" ]; then
    printf 'l9-gate: %s cannot evaluate (%s) — BLOCKING (INV-1: gates fail closed)\n' \
      "$HOOK_NAME" "$reason" >&2
    printf 'l9-gate:   repair with: bash %s/environment/agents/adapters/claude-code/install.sh\n' \
      "$GOV_DIR" >&2
    exit 2
  fi
  printf 'l9-hook: observer %s did NOT run (%s); logged to %s\n' \
    "$HOOK_NAME" "$reason" "$SKIP_LOG" >&2
  record_skip "$reason"
  exit 0
}

[ -f "$GOV_DIR/CANONICAL_LAW.md" ] || cannot_run "no governance SSOT at $GOV_DIR"

HOOK_PATH="$GOV_DIR/environment/agents/adapters/claude-code/hooks/$HOOK_NAME"
[ -f "$HOOK_PATH" ] || cannot_run "hook file absent at $HOOK_PATH"

# Shell hooks carry no locked-dependency requirement, so they are dispatched
# before the interpreter check — demanding a .venv from a bash hook would fail
# it closed for a reason that does not apply to it.
case "$HOOK_NAME" in
  *.sh) exec bash "$HOOK_PATH" ;;
esac

# The locked interpreter, never the sandbox's system python3. The gate modules
# import pydantic/yaml/jsonschema from uv.lock; running them on whatever python
# happens to be on PATH is how a gate starts throwing instead of deciding.
PY="$GOV_DIR/.venv/bin/python3"
[ -x "$PY" ] || PY="$GOV_DIR/.venv/bin/python"
[ -x "$PY" ] || cannot_run "locked interpreter missing under $GOV_DIR/.venv"

exec "$PY" "$HOOK_PATH"
