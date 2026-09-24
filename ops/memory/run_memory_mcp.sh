#!/usr/bin/env bash
# Spawn wrapper for Claude Code's l9-graphite-memory stdio server.
#
# Claude Code expands ${HOME} in the projected .mcp.json, then launches this
# script. The wrapper bind-proves the interpreter so a Dock-started desktop
# session does not need L9_MEMORY_INTERPRETER in the parent environment.
# Resolution stays in ops.memory.runtime_binding (one brain). Fail closed:
# an unbound interpreter never execs a guess.
#
# Every memory this server admits must name the agent that wrote it (ADR-0031):
# the server therefore starts only with the signed agent door. The door is
# minted HERE, at spawn, from one scoped secret in the environment Claude Code
# is started with — L9_MEMORY_AGENT_AUTHORITY_JSON = {"agents_door_secret": …,
# "agent_signing_keys": {"<agent-id>": …}} — or, on a workstation, from the
# local maps export_agent_assertion_env.sh already reads. Grants come from the
# canonical registry, never from the secret. Without a door the server does
# NOT fall back to the anonymous local-operator principal (whose writes carry
# no agent); it refuses to start and says why. L9_MEMORY_ALLOW_LOCAL_OPERATOR=1
# is the explicit, audited operator opt-out.
#
# No env block in .mcp.json. Extra argv from .mcp.json is forwarded.
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

# --- Signed agent door (ADR-0031): every memory names its author ------------
export L9_GOVERNANCE_DIR="$GOV"
# One identity per surface (cursor, claude-code-desktop, claude-code-mobile,
# claude-code-web, …) from the one resolver — never the bare "claude-code".
if ! _agent_id="$(PYTHONPATH="$GOV${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m ops.memory.agent_identity)" \
  || [[ -z "$_agent_id" ]]; then
  echo "run_memory_mcp: no agent identity for this surface (ops/memory/agent_identity.py) — refuse to launch: a memory must name the agent that wrote it" >&2
  exit 1
fi
export L9_MEMORY_AGENT_ID="$_agent_id"
if [[ -n "${L9_MEMORY_AGENT_AUTHORITY_JSON:-}" ]]; then
  _authority_dir="$(mktemp -d "${TMPDIR:-/tmp}/l9-memory-authority.XXXXXX")"
  chmod 700 "$_authority_dir"
  trap 'rm -rf "$_authority_dir"' EXIT
  if ! printf '%s' "$L9_MEMORY_AGENT_AUTHORITY_JSON" \
    | PYTHONPATH="$GOV${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m ops.memory.materialize_agent_authority \
      --agent-id "$L9_MEMORY_AGENT_ID" --governance "$GOV" --output-directory "$_authority_dir"; then
    echo "run_memory_mcp: L9_MEMORY_AGENT_AUTHORITY_JSON is not a valid ${L9_MEMORY_AGENT_ID} authority — refuse to launch" >&2
    exit 1
  fi
  export L9_MEMORY_SECRET_MAP="$_authority_dir/agent_tokens.local.json"
  export L9_MEMORY_GRANTS_MAP="$_authority_dir/agent_grants.json"
fi
unset L9_MEMORY_AGENT_AUTHORITY_JSON L9_MEMORY_HUMAN_DOOR_SECRET
_exporter="$GOV/ops/memory/export_agent_assertion_env.sh"
if [[ ! -f "$_exporter" ]]; then
  echo "run_memory_mcp: $_exporter missing — cannot mint the signed agent door; refuse to launch" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$_exporter"
if [[ -n "${_authority_dir:-}" ]]; then
  rm -rf "$_authority_dir"
  trap - EXIT
fi
_door_missing=()
for _name in L9_MEMORY_AGENTS_DOOR_SECRET L9_MEMORY_AGENT_ASSERTION \
  L9_MEMORY_AGENT_SIGNING_KEYS_JSON L9_MEMORY_AGENT_GRANTS_JSON; do
  [[ -n "${!_name:-}" ]] || _door_missing+=("$_name")
done
if [[ "${#_door_missing[@]}" -ne 0 ]]; then
  if [[ "${L9_MEMORY_ALLOW_LOCAL_OPERATOR:-0}" == "1" ]]; then
    echo "run_memory_mcp: WARNING signed agent door absent (${_door_missing[*]}); L9_MEMORY_ALLOW_LOCAL_OPERATOR=1 — writes carry NO agent identity" >&2
  else
    echo "run_memory_mcp: signed agent door unavailable for ${L9_MEMORY_AGENT_ID} (missing ${_door_missing[*]}) — refuse to launch: a memory must name the agent that wrote it. Provision L9_MEMORY_AGENT_AUTHORITY_JSON in the environment Claude Code starts with (ops/memory/AGENT_WRITE_CONTRACT.md)." >&2
    exit 1
  fi
fi

if [[ $# -gt 0 ]]; then
  exec "$L9_MEMORY_INTERPRETER" "$@"
fi
exec "$L9_MEMORY_INTERPRETER" -m l9_graphite_memory.server --transport stdio
