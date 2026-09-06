#!/usr/bin/env bash
# Shared helpers for the Cursor memory hooks (realignment stage C9).
# SSOT: $HOME/.cursor-governance only (GitHub clone). Dropbox is never consulted.
#
# Since stage C9 this file loads SWITCHES only. It never sources a provider
# defaults file, a machine secrets overlay, or the macOS Keychain, and it never
# exports a provider URL or bearer: memory is reached through the canonical
# control plane (ops/memory), whose runtime resolves its own credentials
# (memory ADR-016). The legacy GRAPHITI_* switch names are honored until the
# provider vocabulary is retired at C11.
set -uo pipefail

graphiti_gov_root() {
  if [ -n "${GLOBAL_COMMANDS:-}" ] && [ -f "$GLOBAL_COMMANDS/ops/memory/control_plane_client.py" ]; then
    printf '%s' "$GLOBAL_COMMANDS"
    return 0
  fi
  if [ -f "$HOME/.cursor-governance/ops/memory/control_plane_client.py" ]; then
    printf '%s' "$HOME/.cursor-governance"
    return 0
  fi
  return 1
}

# Read one switch from the machine-local env file without sourcing it: the
# file may still carry legacy provider lines on an un-migrated machine, and
# sourcing it would put those values into every hook's process.
_l9_switch_from_file() {
  local name="$1" file="$HOME/.cursor/graphiti.env" line
  [ -f "$file" ] || return 1
  line="$(grep -E "^[[:space:]]*(export[[:space:]]+)?${name}=" "$file" 2>/dev/null | tail -n 1)"
  [ -n "$line" ] || return 1
  line="${line#*=}"
  line="${line%\"}"; line="${line#\"}"
  line="${line%\'}"; line="${line#\'}"
  printf '%s' "$line"
}

graphiti_load_env() {
  # Switches only; canonical names first, legacy names honored until C11.
  local enabled gates
  if [ -z "${L9_MEMORY_ENABLED:-}" ] && [ -z "${GRAPHITI_MEMORY_ENABLED:-}" ]; then
    enabled="$(_l9_switch_from_file L9_MEMORY_ENABLED || _l9_switch_from_file GRAPHITI_MEMORY_ENABLED || true)"
    [ -n "$enabled" ] && export GRAPHITI_MEMORY_ENABLED="$enabled"
  fi
  [ -n "${L9_MEMORY_ENABLED:-}" ] && export GRAPHITI_MEMORY_ENABLED="$L9_MEMORY_ENABLED"
  export GRAPHITI_MEMORY_ENABLED="${GRAPHITI_MEMORY_ENABLED:-1}"
  if [ -z "${L9_MEMORY_WRITE_GATES:-}" ] && [ -z "${GRAPHITI_WRITE_GATES:-}" ]; then
    gates="$(_l9_switch_from_file L9_MEMORY_WRITE_GATES || _l9_switch_from_file GRAPHITI_WRITE_GATES || true)"
    [ -n "$gates" ] && export GRAPHITI_WRITE_GATES="$gates"
  fi
  [ -n "${L9_MEMORY_WRITE_GATES:-}" ] && export GRAPHITI_WRITE_GATES="$L9_MEMORY_WRITE_GATES"
  export GRAPHITI_WRITE_GATES="${GRAPHITI_WRITE_GATES:-0}"
  return 0
}

# Legacy: location of the retired provider client. Kept only so an
# un-migrated caller fails at a named path instead of an unbound variable;
# no hook shipped here calls it since C8. Deleted with the client at C11.
graphiti_resolve_cli() {
  REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")"
  RESOLVE="$(dirname "$REAL_HOOK")/../scripts/resolve_governance_paths.sh"
  # shellcheck source=/dev/null
  source "$RESOLVE" 2>/dev/null || true
  if resolve_governance_paths 2>/dev/null; then
    GRAPHITI_CLI="$GLOBAL_COMMANDS/ops/graphiti/graphiti_memory_client.py"
  else
    GRAPHITI_CLI="$HOME/.cursor-governance/ops/graphiti/graphiti_memory_client.py"
  fi
}

graphiti_enabled() {
  graphiti_load_env
  [ "${GRAPHITI_MEMORY_ENABLED:-1}" != "0" ]
}

graphiti_gates_enabled() {
  graphiti_load_env
  [ "${GRAPHITI_WRITE_GATES:-0}" = "1" ]
}

# Canonical, non-authoritative session state (ops/memory/session_state.py).
graphiti_state_file() {
  local conv="${CURSOR_CONVERSATION_ID:-default}"
  local dir="${L9_MEMORY_SESSION_STATE_DIR:-$HOME/.cursor/l9-memory-session-state}"
  echo "$dir/${conv}.json"
}

# Deprecated 2026-08-06: memory-bank scaffolding removed from session hooks.
# Resume SSOT is the canonical memory control plane. Kept as a no-op so
# leftover callers cannot reintroduce T0 silently.
graphiti_scaffold_memory_bank() {
  if [ -z "${GRAPHITI_SCAFFOLD_MEMORY_BANK_WARNED:-}" ]; then
    echo "WARN: graphiti_scaffold_memory_bank is deprecated (no-op); memory-bank removed from session hooks" >&2
    export GRAPHITI_SCAFFOLD_MEMORY_BANK_WARNED=1
  fi
  return 0
}
