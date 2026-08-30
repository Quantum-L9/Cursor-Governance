#!/usr/bin/env bash
# Shared cloud account-environment normalization for Claude Code Web · Mobile.
# Sourced by web/setup.sh, install.sh (hosted repair), and setup.bootstrap.sh
# after the governance clone exists. Keeps the paste stub thin.
#
# Contract: docs/DEGRADED_MODE_CONTRACT.md — capability broker retired; never
# paste secrets into the account variables field.

l9_cloud_env_warn() { printf 'L9 cloud-env WARN: %s\n' "$*" >&2; }
l9_cloud_env_note() { printf 'L9 cloud-env: %s\n' "$*"; }

# Normalize live process env from the account variables field + platform injects.
l9_normalize_cloud_account_env() {
  local gov_dir="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
  local retired leaked leaked_value

  if [ -n "${L9_GOVERNANCE_DIR:-}" ] && [ "$L9_GOVERNANCE_DIR" != "$gov_dir" ]; then
    l9_cloud_env_warn "ignoring L9_GOVERNANCE_DIR='${L9_GOVERNANCE_DIR}' — cloud SSOT is always $gov_dir"
    case "$L9_GOVERNANCE_DIR" in
      *'$HOME'*)
        l9_cloud_env_warn "  UNEXPANDED \$HOME in variables field — delete L9_GOVERNANCE_DIR there"
        ;;
    esac
  fi
  export L9_GOVERNANCE_DIR="$gov_dir"

  if [ -n "${L9_GOVERNANCE_SURFACE:-}" ] && [ "$L9_GOVERNANCE_SURFACE" != "claude-code" ]; then
    l9_cloud_env_warn "L9_GOVERNANCE_SURFACE='${L9_GOVERNANCE_SURFACE}' is not claude-code; using claude-code"
  fi
  export L9_GOVERNANCE_SURFACE="claude-code"

  for retired in \
    L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN \
    L9_CAPABILITY_BROKER_URL; do
    if [ -n "${!retired:-}" ]; then
      l9_cloud_env_warn "$retired is set — retired; delete from the variables field"
      unset "$retired"
    fi
  done

  for leaked in SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN \
                INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD \
                GRAPHITI_MCP_TOKEN AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID \
                AWS_SESSION_TOKEN; do
    leaked_value="${!leaked:-}"
    [ -n "$leaked_value" ] || continue
    if [ "$leaked_value" = "proxy-injected" ]; then
      l9_cloud_env_note "$leaked holds platform proxy sentinel — leaving it"
      continue
    fi
    l9_cloud_env_warn "$leaked is PROHIBITED on this surface; unsetting"
    unset "$leaked"
  done
  # GH_TOKEN / GITHUB_TOKEN: never unset here — platform injects for gh; see
  # docs/DEGRADED_MODE_CONTRACT.md and web/README.md (zizmor may need env -u).

  : "${GRAPHITI_MCP_URL:=https://memory.quantumaipartners.com/graphiti/mcp}"
  export GRAPHITI_MCP_URL
}

# Durable exports for in-session Bash (~/.l9/cloud-session.env).
# $1 = setup.sh exit code (informational only; file is always written).
l9_write_cloud_session_env() {
  local setup_rc="${1:-0}"
  local gov_dir="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
  local stub_revision="${L9_STUB_REVISION:-}"
  local env_file="$HOME/.l9/cloud-session.env"

  mkdir -p "$(dirname "$env_file")"
  {
    echo "# Written by L9 cloud_account_env.sh — do not edit by hand."
    [ -n "$stub_revision" ] && echo "export L9_STUB_REVISION=$(printf %q "$stub_revision")"
    echo "export L9_GOVERNANCE_DIR=$(printf %q "$gov_dir")"
    echo "export L9_GOVERNANCE_SURFACE=claude-code"
    echo "export GRAPHITI_MCP_URL=$(printf %q "${GRAPHITI_MCP_URL:-}")"
    echo "unset L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN"
    echo "unset L9_CAPABILITY_BROKER_URL"
    echo "unset GRAPHITI_MCP_TOKEN INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD"
    echo "unset SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN"
    echo "unset AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID AWS_SESSION_TOKEN"
  } > "$env_file"

  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    cat "$env_file" >> "$CLAUDE_ENV_FILE"
    l9_cloud_env_note "durable env appended to CLAUDE_ENV_FILE"
  else
    local profile
    for profile in "$HOME/.bashrc" "$HOME/.profile"; do
      [ -f "$profile" ] || touch "$profile"
      grep -qF 'cloud-session.env' "$profile" 2>/dev/null \
        || printf '%s\n' '. "$HOME/.l9/cloud-session.env"  # L9 governed session env' >> "$profile"
    done
    l9_cloud_env_note "sourcing $env_file from shell profile"
  fi

  return "$setup_rc"
}

l9_report_cloud_memory_posture() {
  l9_cloud_env_note "memory front door: ${GRAPHITI_MCP_URL:-unset} (no bearer)"
  l9_cloud_env_note "capability plane: RETIRED (never shipped)"
}
