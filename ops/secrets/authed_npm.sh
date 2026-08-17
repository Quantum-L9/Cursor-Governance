#!/usr/bin/env bash
# L9-TRUSTED-OPERATOR-ONLY
# Resolve Infisical GITHUB_TOKEN (sole agent PAT) and exec the given command
# with npm GitHub Packages auth via the npm_config_ env convention.
# Plain NODE_AUTH_TOKEN is NOT honored by npm for scoped registries unless an
# .npmrc line maps it. This wrapper is trusted-operator only — a model-
# controlled surface must use github.packages_read, not possess the PAT.
#
# Usage:
#   ops/secrets/authed_npm.sh npm ci
#   ops/secrets/authed_npm.sh npm publish
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
GOV="$(cd "$HERE/../.." && pwd)"
PY="${GOV}/.venv/bin/python"
[ -x "$PY" ] || PY="python3"

if [ "$#" -eq 0 ]; then
  echo "authed_npm: usage: authed_npm.sh <command> [args...]" >&2
  exit 2
fi

# Refuse inside a model-controlled runtime. Do not fall back to AWS.
TOKEN="$(
  cd "$GOV" && "$PY" -c '
import sys
from pathlib import Path
sys.path.insert(0, str(Path("ops/secrets").resolve()))
from surface_trust import require_trusted
from hydrate_infisical import bootstrap_config, fetch_values

require_trusted()
cfg = bootstrap_config()
if cfg is None:
    raise SystemExit("authed_npm: Infisical operator credentials missing (no AWS fallback)")
values = fetch_values(cfg)
token = (values.get("GITHUB_TOKEN") or values.get("GH_TOKEN") or "").strip()
if not token:
    raise SystemExit("authed_npm: GITHUB_TOKEN missing from Infisical")
print(token)
'
)" || {
  status=$?
  echo "authed_npm: PRIVATE_REGISTRY_UNREACHABLE (trusted-operator Infisical path refused or unavailable)" >&2
  exit "$status"
}

if [ -z "$TOKEN" ]; then
  echo "authed_npm: PRIVATE_REGISTRY_UNREACHABLE" >&2
  exit 1
fi

exec env "npm_config_//npm.pkg.github.com/:_authToken=$TOKEN" "$@"
