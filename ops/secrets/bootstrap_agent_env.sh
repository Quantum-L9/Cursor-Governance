#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Canonical secret bootstrap for EVERY agent surface.
#
# Surface-agnostic by construction. Claude Code, Codex, Gemini, Manus, the
# generic adapter, Cursor and CI all call this identical script; none of them
# owns a private copy of the bootstrap, and none of them keeps its own secret
# inventory. ops/secrets is the SSOT (CANONICAL_LAW §14).
#
#   <adapter installer>  ->  ops/secrets/bootstrap_agent_env.sh  ->  ops/secrets/*
#
# Credential precedence (see l9-aws-secrets, references/infisical-protocol.md):
#   1. INFISICAL_CLIENT_ID / INFISICAL_CLIENT_SECRET already in the environment
#      — the path for sandboxes with no AWS CLI (Claude Code cloud, Manus, CI).
#   2. AWS ref openclaw-igorbot/infisical-cursor-governance — the documented
#      chicken-egg bootstrap, used wherever the AWS CLI is configured.
#
# Values are never printed, logged, or written to a receipt. `--check` asks the
# provider for names only. Adding a surface must never mean adding a secret to
# an adapter env file: register it in ops/secrets and resolve it here.
#
# Usage:
#   bootstrap_agent_env.sh --check [--require A,B] [--surface <id>]
#   eval "$(bootstrap_agent_env.sh --export SONAR_TOKEN,SEMGREP_APP_TOKEN)"
#
# Exit 0 when every required name is available, 1 otherwise. Callers decide
# whether that is fatal; an adapter should degrade and report, not abort.
# ---------------------------------------------------------------------------
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOV_ROOT="$(cd "$HERE/../.." && pwd)"

MODE="--check"
REQUIRE=""
EXPORT_NAMES=""
SURFACE="${L9_GOVERNANCE_SURFACE:-unknown}"

while [ $# -gt 0 ]; do
  case "$1" in
    --check)   MODE="--check"; shift ;;
    --export)  MODE="--export"; EXPORT_NAMES="${2:?--export needs names}"; shift 2 ;;
    --require) REQUIRE="${2:?--require needs names}"; shift 2 ;;
    --surface) SURFACE="${2:?--surface needs an id}"; shift 2 ;;
    -h|--help) sed -n '2,29p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "bootstrap_agent_env: unknown argument '$1'" >&2; exit 2 ;;
  esac
done

# Locked interpreter when present — same rule every other governance entrypoint
# uses, so the provider client runs on the pinned Python rather than whatever
# system python3 happens to be.
PY="$GOV_ROOT/.venv/bin/python3"
[ -x "$PY" ] || PY="python3"

HYDRATE="$HERE/hydrate_infisical.py"
if [ ! -f "$HYDRATE" ]; then
  echo "bootstrap_agent_env: missing $HYDRATE" >&2
  exit 1
fi

# Fill in Universal Auth from AWS when the environment did not supply it and the
# AWS CLI is available. resolve_secret.py is the canonical AWS resolver; its
# stdout is captured into this process only and never echoed.
if [ -z "${INFISICAL_CLIENT_ID:-}" ] || [ -z "${INFISICAL_CLIENT_SECRET:-}" ]; then
  if command -v aws >/dev/null 2>&1 && [ -f "$HERE/resolve_secret.py" ]; then
    for field in client_id client_secret project_id; do
      value="$("$PY" "$HERE/resolve_secret.py" \
        --ref "openclaw-igorbot/infisical-cursor-governance#${field}" 2>/dev/null)" || value=""
      [ -n "$value" ] || continue
      case "$field" in
        client_id)     export INFISICAL_CLIENT_ID="$value" ;;
        client_secret) export INFISICAL_CLIENT_SECRET="$value" ;;
        project_id)    export INFISICAL_PROJECT_ID="$value" ;;
      esac
    done
    unset value
  fi
fi

if [ "$MODE" = "--export" ]; then
  exec "$PY" "$HYDRATE" --export "$EXPORT_NAMES"
fi

echo "secret bootstrap: surface=${SURFACE} provider=infisical (ops/secrets SSOT)"
if [ -n "$REQUIRE" ]; then
  "$PY" "$HYDRATE" --check --require "$REQUIRE"
else
  "$PY" "$HYDRATE" --check
fi
rc=$?

if [ "$rc" -ne 0 ]; then
  # Every ref below is registered and provisioned in
  # ops/secrets/openclaw-igorbot.registry.yaml — a failure here is delivery,
  # not a missing secret, so point at delivery rather than asking for new ones.
  echo "secret bootstrap: DEGRADED — provider unreachable for surface '${SURFACE}'" >&2
  echo "  supply INFISICAL_CLIENT_ID / INFISICAL_CLIENT_SECRET to this surface," >&2
  echo "  or configure the AWS CLI so openclaw-igorbot/infisical-cursor-governance resolves." >&2
fi
exit "$rc"
