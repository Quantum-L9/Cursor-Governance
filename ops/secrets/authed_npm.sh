#!/usr/bin/env bash
# Resolve the sole agent PAT (openclaw-igorbot/github#token) and exec the given
# command with npm GitHub Packages auth exported via the npm_config_ env
# convention. Plain `NODE_AUTH_TOKEN` is NOT honored by npm for scoped
# registries unless an .npmrc line maps it — this wrapper makes scoped
# installs/publishes work from any clone without inline flags.
#
# Usage:
#   ops/secrets/authed_npm.sh npm ci
#   ops/secrets/authed_npm.sh npm publish
set -euo pipefail

GOV="${HOME}/.cursor-governance"
[ -d "$GOV/ops/secrets" ] || GOV="${HOME}/Cursor-Governance"
PY="${GOV}/.venv/bin/python"
[ -x "$PY" ] || PY="python3"

TOKEN="$(cd "$GOV" && "$PY" ops/secrets/resolve_secret.py --ref 'openclaw-igorbot/github#token')"
if [ -z "$TOKEN" ]; then
  echo "authed_npm: failed to resolve openclaw-igorbot/github#token" >&2
  exit 1
fi

if [ "$#" -eq 0 ]; then
  echo "authed_npm: usage: authed_npm.sh <command> [args...]" >&2
  exit 2
fi

exec env "npm_config_//npm.pkg.github.com/:_authToken=$TOKEN" "$@"
