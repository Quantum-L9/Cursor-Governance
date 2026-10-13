#!/usr/bin/env bash
# Export the ADR-0031 agent MCP assertion env for ONE principal into the
# CURRENT shell — the shell that is about to launch the host (Cursor, Claude
# Code) whose MCP server must inherit it. This is the pre-launch handoff: a
# SessionStart hook runs as a child of the host and cannot deliver env to the
# host or to the separately launched l9-graphite-memory server, so source this
# BEFORE starting the host.
#
# Exports only $AGENT_ID's signing key and grant entry (never a peer's, never
# the whole map). NEVER exports L9_MEMORY_HUMAN_DOOR_SECRET.
# Safe to `source`: missing maps return without exiting the caller.
# Leaves L9_ASSERTION_EXPORT_STATUS (a shell variable, never exported) set to
# minted | skipped | failed, so a sourcing launcher can tell a mint that was
# never attempted from one that was refused.
# shellcheck disable=SC2034,SC2317  # status is read by the sourcing launcher; `exit` runs when executed
set -uo pipefail
L9_ASSERTION_EXPORT_STATUS=skipped
AGENT_ID="${L9_MEMORY_AGENT_ID:-}"
SECRET_MAP="${L9_MEMORY_SECRET_MAP:-$HOME/.config/l9-memory/agent_tokens.local.json}"
GRANTS_MAP="${L9_MEMORY_GRANTS_MAP:-$HOME/.config/l9-memory/agent_grants.json}"
GOV_ROOT="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
# Prefer the bound memory interpreter; the helper's fallback mint uses the
# package wire format, so python3 without the package still mints a token the
# server verifies.
PY="${L9_MEMORY_INTERPRETER:-python3}"
# Every early stop is a top-level `return` (ends a sourced run without exiting
# the caller) falling back to `exit` when executed. A `return` inside a helper
# function would end only that function, and the script would run on.
if [[ ! -f "$SECRET_MAP" || ! -f "$GRANTS_MAP" ]]; then
  echo "assertion env skipped: secret/grants map missing (memory-blind OK)" >&2
  return 0 2>/dev/null || exit 0
fi
# No fallback author: an unset L9_MEMORY_AGENT_ID is derived from host
# evidence, and with none no assertion is minted.
if [[ -z "$AGENT_ID" ]]; then
  AGENT_ID="$(PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$GOV_ROOT" "$PY" -m ops.memory.agent_identity 2>/dev/null || true)"
fi
if [[ -z "$AGENT_ID" ]]; then
  echo "assertion env skipped: no memory identity (set L9_MEMORY_AGENT_ID or run under a host)" >&2
  return 0 2>/dev/null || exit 0
fi
# The helper refuses a terminal stdout and writes secrets to a 0600 file.
# stdout is only that path; source it, then unlink.
_assert_rc=0
_assert_path="$(
  PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$GOV_ROOT" \
    "$PY" "$GOV_ROOT/ops/memory/print_agent_assertion_env.py" \
    --agent-id "$AGENT_ID" \
    --secret-map "$SECRET_MAP" \
    --grants-map "$GRANTS_MAP" \
    --format shell
)" || _assert_rc=$?
if [[ -n "${_assert_path:-}" && -f "$_assert_path" ]]; then
  # shellcheck disable=SC1090
  source "$_assert_path"
  rm -f "$_assert_path"
  L9_ASSERTION_EXPORT_STATUS=minted
else
  # The maps exist and an identity resolved, yet the helper produced no env
  # file (its stderr names why). Say so: a refused mint must not read like a
  # skipped one.
  L9_ASSERTION_EXPORT_STATUS=failed
  echo "assertion env NOT minted for $AGENT_ID (print_agent_assertion_env.py exit $_assert_rc)" >&2
fi
return 0 2>/dev/null || exit 0
