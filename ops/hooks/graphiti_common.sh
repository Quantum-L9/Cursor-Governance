#!/usr/bin/env bash
# Shared helpers for Graphiti Cursor hooks.
# SSOT: $HOME/.cursor-governance only (GitHub clone). Dropbox is never consulted.
set -uo pipefail

graphiti_gov_root() {
  if [ -n "${GLOBAL_COMMANDS:-}" ] && [ -f "$GLOBAL_COMMANDS/ops/graphiti/graphiti.env.defaults" ]; then
    printf '%s' "$GLOBAL_COMMANDS"
    return 0
  fi
  if [ -f "$HOME/.cursor-governance/ops/graphiti/graphiti.env.defaults" ]; then
    printf '%s' "$HOME/.cursor-governance"
    return 0
  fi
  return 1
}

graphiti_load_env() {
  local defaults="" root=""
  root="$(graphiti_gov_root 2>/dev/null || true)"
  if [ -n "$root" ]; then
    defaults="$root/ops/graphiti/graphiti.env.defaults"
  fi
  # shellcheck disable=SC1090
  [ -n "$defaults" ] && [ -f "$defaults" ] && set -a && source "$defaults" && set +a
  # shellcheck disable=SC1090
  [ -f "$HOME/.cursor/graphiti.env" ] && set -a && source "$HOME/.cursor/graphiti.env" && set +a
  # shellcheck disable=SC1090
  [ -f "$HOME/.cursor/secrets/graphiti.env" ] && set -a && source "$HOME/.cursor/secrets/graphiti.env" && set +a
  # Token: machine secrets file first; macOS Keychain only if `security` exists.
  if [ -z "${GRAPHITI_MCP_TOKEN:-}" ]; then
    if command -v security >/dev/null 2>&1; then
      GRAPHITI_MCP_TOKEN="$(security find-generic-password -s graphiti-mcp-token -w 2>/dev/null || true)"
      export GRAPHITI_MCP_TOKEN
    fi
  fi
  if [ -z "${GRAPHITI_MCP_TOKEN:-}" ] && [ ! -f "$HOME/.cursor/secrets/graphiti.env" ]; then
    # Linux / containers: Keychain is absent — secrets file is the intended path.
    : # callers may warn; keep fail-open
  fi
}

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

graphiti_state_file() {
  local conv="${CURSOR_CONVERSATION_ID:-default}"
  echo "$HOME/.cursor/graphiti-state/${conv}.json"
}

graphiti_scaffold_memory_bank() {
  local repo="${1:-${CURSOR_PROJECT_DIR:-}}"
  local template_dir=""
  graphiti_resolve_cli
  template_dir="$(dirname "$GRAPHITI_CLI")/memory-bank-template"
  [ -d "$template_dir" ] || return 0
  local bank="$repo/memory-bank"
  mkdir -p "$bank"
  for f in activeContext.md tasks.md progress.md tech-debt.md; do
    if [ ! -f "$bank/$f" ]; then
      cp "$template_dir/$f" "$bank/$f"
    fi
  done
}
