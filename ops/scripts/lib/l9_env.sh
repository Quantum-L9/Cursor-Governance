#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Resolve the L9 session environment from a NON-LOGIN shell.
#
# setup.bootstrap.sh writes ~/.l9/cloud-session.env and appends a `source` line
# to ~/.bashrc and ~/.profile. Neither is read by a non-interactive, non-login
# shell — which is exactly what an agent's Bash tool spawns. The audited session
# proved it: `bash -lc 'echo $L9_GOVERNANCE_DIR'` printed the path while the
# same expansion in the tool's own shell printed nothing (finding B-18).
#
# BASH_ENV would fix it for children, but it has to be present in the ALREADY
# RUNNING agent process to matter, and a setup script that ran at environment
# build time cannot reach back into it. So consumers resolve through this helper
# instead, which sources the durable file on demand and falls back to the
# contract's fixed default.
#
# Sourcing is idempotent and never overrides an explicitly exported value.
# ---------------------------------------------------------------------------

# shellcheck shell=bash

#: The cloud SSOT. Fixed by contract, never guessed.
L9_DEFAULT_GOVERNANCE_DIR="$HOME/.cursor-governance"

l9_load_session_env() {
  if [ -z "${L9_GOVERNANCE_DIR:-}" ]; then
    local env_file="${L9_SESSION_ENV_FILE:-$HOME/.l9/cloud-session.env}"
    # shellcheck disable=SC1090
    [ -f "$env_file" ] && . "$env_file"
  fi
  # An unexpanded literal '$HOME' arrives from .env-format fields, which perform
  # no shell expansion. It names a directory that does not exist; refuse it.
  case "${L9_GOVERNANCE_DIR:-}" in
    *'$HOME'*|*'${HOME}'*) L9_GOVERNANCE_DIR="" ;;
  esac
  : "${L9_GOVERNANCE_DIR:=$L9_DEFAULT_GOVERNANCE_DIR}"
  export L9_GOVERNANCE_DIR
}

l9_governance_dir() {
  l9_load_session_env
  printf '%s' "$L9_GOVERNANCE_DIR"
}
