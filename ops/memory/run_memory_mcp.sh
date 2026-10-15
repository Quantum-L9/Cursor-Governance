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
# minted HERE, at spawn, from the local maps export_agent_assertion_env.sh
# reads (~/.config/l9-memory). A hosted container mints those maps itself — at
# environment setup (web/setup.sh) and, failing that, here — so nothing secret
# is ever pasted into the account environment settings. A workstation adds its
# key once. A launcher that deliberately supplies one scoped secret,
# L9_MEMORY_AGENT_AUTHORITY_JSON = {"agents_door_secret": …,
# "agent_signing_keys": {"<agent-id>": …}}, still takes precedence. Grants come from the
# canonical registry, never from the secret. Without a door the server does
# NOT fall back to the anonymous local-operator principal (whose writes carry
# no agent); it refuses to start and says why. L9_MEMORY_ALLOW_LOCAL_OPERATOR=1
# is the explicit, audited operator opt-out.
#
# No env block in .mcp.json. Extra argv from .mcp.json is forwarded.
set -euo pipefail

# The checkout that contains this script is the governance tree it binds.
# $HOME/.cursor-governance remains the fallback for a copied wrapper.
# L9_GOVERNANCE_DIR still wins when a caller names a tree on purpose.
_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_script_gov="$(cd "$_script_dir/../.." && pwd)"
if [[ -n "${L9_GOVERNANCE_DIR:-}" ]]; then
  GOV="$L9_GOVERNANCE_DIR"
elif [[ -f "$_script_gov/CANONICAL_LAW.md" ]]; then
  GOV="$_script_gov"
else
  GOV="$HOME/.cursor-governance"
fi
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

# The MCP server is started in parallel with the SessionStart hook that may be
# installing this .venv. Wait for the install before binding (which imports the
# package) and before exec; a half-installed venv is refused by name rather
# than crashing on import. Lazy imports after a LATER reinstall are not covered:
# the server is long-lived and holds no lock across its lifetime.
if [[ -f "$GOV/ops/scripts/lib/venv_ready.sh" ]]; then
  # shellcheck source=/dev/null
  . "$GOV/ops/scripts/lib/venv_ready.sh"
  _ready_rc=0
  venv_ready_wait "$GOV" || _ready_rc=$?
  if [[ "$_ready_rc" -eq 2 ]]; then
    echo "run_memory_mcp: refuse to launch on a half-installed governance venv" >&2
    exit 1
  fi
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
# The identity is DERIVED from host markers by the one resolver (cursor,
# claude-code). Desktop and mobile are surfaces, not authors.
if ! _agent_id="$(PYTHONPATH="$GOV${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m ops.memory.agent_identity)" \
  || [[ -z "$_agent_id" ]]; then
  echo "run_memory_mcp: no agent identity for this surface (ops/memory/agent_identity.py) — refuse to launch: a memory must name the agent that wrote it" >&2
  exit 1
fi
export L9_MEMORY_AGENT_ID="$_agent_id"

# --- Transport selection (ADR-0053, CANONICAL_LAW §8.10) ---------------------
# Local stdio is the default. An operator selects the admitted remote service
# by naming its endpoint (L9_MEMORY_REMOTE_MCP_ENDPOINT, or the per-machine
# address file for Dock-launched hosts). The model-visible entry never changes:
# this wrapper then execs the consumer bridge instead of the local server. A
# requested remote transport that cannot be proven refuses to launch; it never
# falls back to the local store.
# The bridge runs on the governance Python, pinned here: the exporter sourced
# below reassigns PY to the memory interpreter.
_gov_py="$PY"
_remote_config="${L9_MEMORY_REMOTE_CONFIG:-$HOME/.config/l9-memory/remote-endpoint.json}"
_transport=local
if [[ -n "${L9_MEMORY_REMOTE_MCP_ENDPOINT:-}" || -e "$_remote_config" ]]; then
  if ! _transport="$(PYTHONPATH="$GOV${PYTHONPATH:+:$PYTHONPATH}" "$_gov_py" -m ops.memory_remote.bridge --check)" \
    || [[ "$_transport" != "remote" ]]; then
    echo "run_memory_mcp: remote memory transport requested but not admissible (ops/memory_remote/bridge.py) — refuse to launch; no fallback to the local store" >&2
    exit 1
  fi
  if [[ "${L9_MEMORY_ALLOW_LOCAL_OPERATOR:-0}" == "1" ]]; then
    echo "run_memory_mcp: L9_MEMORY_ALLOW_LOCAL_OPERATOR=1 is local-only; the remote transport admits signed agents only — refuse to launch" >&2
    exit 1
  fi
  if [[ $# -gt 0 && "$*" != "-m l9_graphite_memory.server --transport stdio" ]]; then
    echo "run_memory_mcp: remote transport takes no server argv (got: $*) — refuse to launch" >&2
    exit 1
  fi
  if [[ -z "${L9_MEMORY_AGENT_AUTHORITY_JSON:-}" \
    && "$(printf '%s' "${CLAUDE_CODE_REMOTE:-}" | tr '[:upper:]' '[:lower:]')" == "true" ]]; then
    # The hosted self-mint below makes a key only this container knows: valid
    # against an in-process server, never against a remote one. Say so rather
    # than mint a key the service can only reject.
    echo "run_memory_mcp: remote memory needs a durable per-agent signing key provisioned to the service; a container-minted key cannot authenticate remotely — refuse to launch (ADR-0053)" >&2
    exit 1
  fi
fi

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
elif [[ "$(printf '%s' "${CLAUDE_CODE_REMOTE:-}" | tr '[:upper:]' '[:lower:]')" == "true" ]]; then
  # A hosted container with no authority in its environment: mint (or reuse)
  # the container-local authority the exporter below reads. The server verifies
  # against keys handed to this very process, so an in-container key is as
  # valid as a workstation one, and no secret ever goes in the plaintext,
  # model-readable environment settings. Additive and idempotent; web/setup.sh
  # normally did this already. stdout is the MCP channel: report on stderr.
  PYTHONPATH="$GOV${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m ops.memory.materialize_agent_authority \
    --provision-hosted --governance "$GOV" --agent-id "$L9_MEMORY_AGENT_ID" >&2 \
    || echo "run_memory_mcp: hosted authority provisioning FAILED for ${L9_MEMORY_AGENT_ID}" >&2
fi
unset L9_MEMORY_AGENT_AUTHORITY_JSON L9_MEMORY_HUMAN_DOOR_SECRET
_exporter="$GOV/ops/memory/export_agent_assertion_env.sh"
if [[ ! -f "$_exporter" ]]; then
  echo "run_memory_mcp: $_exporter missing — cannot mint the signed agent door; refuse to launch" >&2
  exit 1
fi
# The six Tier-2 admission values the server reads. The server verifies the
# signature, digest, and actor; this gate only refuses to exec without them.
_door_names=(L9_MEMORY_AGENTS_DOOR_SECRET L9_MEMORY_AGENT_ASSERTION
  L9_MEMORY_AGENT_SIGNING_KEYS_JSON L9_MEMORY_AGENT_GRANTS_JSON
  L9_MEMORY_IDENTITY_ASSERTION_JSON L9_MEMORY_IDENTITY_ASSERTION_HMAC)
L9_ASSERTION_EXPORT_STATUS=""
# shellcheck source=/dev/null
source "$_exporter"
if [[ -n "${_authority_dir:-}" ]]; then
  rm -rf "$_authority_dir"
  trap - EXIT
fi
if [[ "${L9_ASSERTION_EXPORT_STATUS:-}" == "failed" ]]; then
  # A refused mint leaves whatever door the parent environment carried. Drop
  # it rather than launch on stale values that merely look complete.
  echo "run_memory_mcp: signed agent door mint FAILED for ${L9_MEMORY_AGENT_ID} — inherited door values discarded" >&2
  unset "${_door_names[@]}"
fi
_door_missing=()
for _name in "${_door_names[@]}"; do
  [[ -n "${!_name:-}" ]] || _door_missing+=("$_name")
done
if [[ "${#_door_missing[@]}" -ne 0 ]]; then
  if [[ "${L9_MEMORY_ALLOW_LOCAL_OPERATOR:-0}" == "1" ]]; then
    echo "run_memory_mcp: WARNING signed agent door absent (${_door_missing[*]}); L9_MEMORY_ALLOW_LOCAL_OPERATOR=1 — writes carry NO agent identity" >&2
  else
    echo "run_memory_mcp: signed agent door unavailable for ${L9_MEMORY_AGENT_ID} (missing ${_door_missing[*]}) — refuse to launch: a memory must name the agent that wrote it. A hosted container mints it itself (materialize_agent_authority --provision-hosted); a workstation adds its key once with --add-keys-to (ops/memory/AGENT_WRITE_CONTRACT.md)." >&2
    exit 1
  fi
fi

if [[ "$_transport" == "remote" ]]; then
  # The bridge keeps only {agent_id: key} and the sealed identity, and drops
  # every server-side value (door secret, grants) before it serves: the
  # remote service owns grants and verifies against its own key registry.
  PYTHONPATH="$GOV${PYTHONPATH:+:$PYTHONPATH}" exec "$_gov_py" -m ops.memory_remote.bridge --serve
fi
if [[ $# -gt 0 ]]; then
  exec "$L9_MEMORY_INTERPRETER" "$@"
fi
exec "$L9_MEMORY_INTERPRETER" -m l9_graphite_memory.server --transport stdio
