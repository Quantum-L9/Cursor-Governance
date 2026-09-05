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

# INV-1b: the class is a property of the HOOK, not of the caller.
#
# This file exists so the fail-open/fail-closed decision is made once rather
# than re-typed inside eight `bash -c '...'` one-liners where a copy-paste slip
# silently disables a gate. It took --class on trust, so the slip it was built
# to prevent still worked: `--class observer memory_gate.py` exits 0 and the
# gate never evaluates, which is indistinguishable from a gate that passed.
#
# The table below is the authority. A registration that disagrees with it is a
# malformed registration, and malformed registrations already refuse to guess.
# A hook absent from the table keeps the caller's class, so adding an observer
# needs no edit here; every GATE is named, because that is the direction where
# being wrong is silent.
l9_required_class() {
  case "$1" in
    merge_gate_wrap.py|local_execution_gate_wrap.py|memory_gate.py|session_debt_wrap.py)
      printf 'gate' ;;
    *) printf '' ;;
  esac
}

_L9_REQUIRED="$(l9_required_class "$HOOK_NAME")"
if [ -n "$_L9_REQUIRED" ] && [ "$_L9_REQUIRED" != "$HOOK_CLASS" ]; then
  printf 'l9-hook: %s is registered --class %s but is a %s — refusing to downgrade it\n' \
    "$HOOK_NAME" "$HOOK_CLASS" "$_L9_REQUIRED" >&2
  exit 2
fi
unset _L9_REQUIRED

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

# Surface guard (INV-2): Claude gate-class hooks must not evaluate under Cursor
# (or any non-Claude surface). Cursor has its own ~/.cursor/hooks.json stack.
# Fail toward enforcing: unknown surface still runs the gate. Kill switch:
# L9_SURFACE_GUARD=0 restores the pre-guard behavior for diagnostics.
# SSOT: ops/scripts/lib/surface_detect.sh (resolved via GOV_DIR, else this tree).
if [ "$HOOK_CLASS" = "gate" ] && [ "${L9_SURFACE_GUARD:-1}" != "0" ]; then
  _L9_HOOK_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  _L9_SD_LIB=""
  _L9_WALK="$_L9_HOOK_DIR"
  while [ -n "$_L9_WALK" ] && [ "$_L9_WALK" != "/" ]; do
    if [ -f "$_L9_WALK/ops/scripts/lib/surface_detect.sh" ]; then
      _L9_SD_LIB="$_L9_WALK/ops/scripts/lib/surface_detect.sh"
      break
    fi
    _L9_WALK="$(dirname "$_L9_WALK")"
  done
  if [ -z "$_L9_SD_LIB" ] && [ -f "$GOV_DIR/ops/scripts/lib/surface_detect.sh" ]; then
    _L9_SD_LIB="$GOV_DIR/ops/scripts/lib/surface_detect.sh"
  fi
  if [ -n "$_L9_SD_LIB" ] && [ -f "$_L9_SD_LIB" ]; then
    # shellcheck source=../../../../ops/scripts/lib/surface_detect.sh
    . "$_L9_SD_LIB"
    _L9_SURFACE="$(l9_detect_surface)"
    # Skip only Claude-only gates (memory + local-execution). merge_gate and
    # session_debt stay active on Cursor — Cursor's native stack does not
    # replace those authorizations. unknown fails toward enforcing.
    case "$_L9_SURFACE" in
      claude-code|claude-code-remote|unknown) : ;;
      *)
        case "$HOOK_NAME" in
          local_execution_gate_wrap.py|memory_gate.py)
            printf 'l9-hook: gate %s skipped (surface=%s; Claude-only gate)\n' \
              "$HOOK_NAME" "$_L9_SURFACE" >&2
            unset _L9_SURFACE
            exit 0
            ;;
        esac
        ;;
    esac
    unset _L9_SURFACE
  fi
  unset _L9_SD_LIB _L9_WALK _L9_HOOK_DIR
fi

SKIP_LOG="${L9_HOOK_SKIP_LOG:-$HOME/.l9/claude/hook-skips.log}"

# Every skip is timestamped in UTC. An undated skip log cannot answer the only
# question worth asking of it: was this hook skipped during the run I am
# investigating, or six weeks ago?
# The skip log answers one question: was this hook skipped during the run I am
# investigating? It used to `return 0` when its directory could not be created,
# so the record vanished in exactly the broken-environment case it exists for —
# a wrong or unwritable HOME is what makes hooks skip in the first place. It now
# falls back to TMPDIR and says on stderr where the line actually went.
record_skip() {
  local reason="$1" ts target
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 'unknown-time')"
  target="$SKIP_LOG"
  if ! mkdir -p "$(dirname "$target")" 2>/dev/null; then
    target="${TMPDIR:-/tmp}/l9-hook-skips.log"
    printf 'l9-hook: skip log unwritable at %s — recording to %s\n' "$SKIP_LOG" "$target" >&2
  fi
  if ! printf '%s observer %s %s\n' "$ts" "$HOOK_NAME" "$reason" >> "$target" 2>/dev/null; then
    printf 'l9-hook: could not record skip of %s (%s) anywhere\n' "$HOOK_NAME" "$reason" >&2
  fi
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
