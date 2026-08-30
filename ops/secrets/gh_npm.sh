#!/usr/bin/env bash
# Wire npm GitHub Packages to `gh auth token` (same identity git/gh already use).
# Never prints the token. Does not read NODE_AUTH_TOKEN or Infisical.
# Trusted-operator Infisical path remains ops/secrets/authed_npm.sh.
#
# Usage:
#   ops/secrets/gh_npm.sh npm ci
#   ops/secrets/gh_npm.sh --install-userconfig   # hosted Claude only (ephemeral ~/.npmrc)
set -euo pipefail

_token() {
  command -v gh >/dev/null 2>&1 || {
    echo "gh_npm: gh CLI not on PATH" >&2
    return 1
  }
  gh auth token 2>/dev/null || {
    echo "gh_npm: gh auth token failed" >&2
    return 1
  }
}

install_userconfig() {
  local tok
  tok="$(_token)" || return 1
  if [ -z "$tok" ]; then
    echo "gh_npm: empty token" >&2
    return 1
  fi
  command -v npm >/dev/null 2>&1 || {
    echo "gh_npm: npm not on PATH" >&2
    return 1
  }
  npm config set "//npm.pkg.github.com/:_authToken" "$tok" --location user >/dev/null 2>&1
}

if [ "${1:-}" = "--install-userconfig" ]; then
  install_userconfig
  exit $?
fi

if [ "$#" -eq 0 ]; then
  echo "gh_npm: usage: gh_npm.sh [--install-userconfig] <command> [args...]" >&2
  exit 2
fi

tok="$(_token)" || exit 1
if [ -z "$tok" ]; then
  echo "gh_npm: empty token" >&2
  exit 1
fi
exec env "npm_config_//npm.pkg.github.com/:_authToken=$tok" "$@"
