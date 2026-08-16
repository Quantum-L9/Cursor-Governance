#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Canonical capability bootstrap for EVERY agent surface.
#
# Surface-agnostic by construction. Claude Code, Codex, Gemini, Manus, the
# generic adapter, Cursor and CI all call this identical script; none of them
# owns a private copy, and none keeps its own secret inventory. ops/secrets is
# the SSOT (CANONICAL_LAW §14).
#
#   <adapter installer>  ->  ops/secrets/bootstrap_agent_env.sh  ->  capability plane
#
# WHAT CHANGED, AND WHY IT CANNOT CHANGE BACK
#
# This script used to hydrate raw secrets into the agent's environment, taking
# INFISICAL_CLIENT_SECRET from the surface or falling back to an AWS-resolved
# Universal Auth credential. Both paths are gone for model-controlled surfaces.
# The reasoning is simple and not negotiable: everything an LLM can execute can
# read that LLM's environment, filesystem and child processes. A secret placed
# there is a secret the model possesses, regardless of how carefully the code
# around it is written. So the model is given CAPABILITY NAMES and the broker
# keeps the credentials.
#
#   old:  surface -> Infisical -> export SONAR_TOKEN -> model-controlled process
#   new:  surface -> named capability -> broker -> Infisical -> upstream
#
# Execution classes (ops/secrets/surface_trust.py decides, not this script):
#
#   model-controlled   claude-code, codex, gemini, manus, cursor, generic, and
#                      EVERY unregistered surface. Capabilities only. `--export`
#                      is denied. No AWS read. No INFISICAL_CLIENT_SECRET read.
#   trusted-operator   an explicit `--surface operator` from a runtime with no
#                      model-control markers. Retains raw resolution for humans.
#
# Trust is never inferred from the absence of a known surface id: an unknown
# surface is model-controlled, so a new adapter cannot acquire secret access by
# forgetting to register (contract R2).
#
# Usage:
#   bootstrap_agent_env.sh --check --surface <id> [--require-capabilities a,b]
#   bootstrap_agent_env.sh --surface operator --export SONAR_TOKEN   # humans only
#
# Exit 0 when every required capability is ENABLED, 1 otherwise. Callers decide
# whether that is fatal; an adapter should degrade and report, not abort.
# ---------------------------------------------------------------------------
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOV_ROOT="$(cd "$HERE/../.." && pwd)"

MODE="--check"
REQUIRE_CAPS=""
EXPORT_NAMES=""
SURFACE="${L9_GOVERNANCE_SURFACE:-unknown}"

while [ $# -gt 0 ]; do
  case "$1" in
    --check)   MODE="--check"; shift ;;
    --export)  MODE="--export"; EXPORT_NAMES="${2:?--export needs names}"; shift 2 ;;
    --require-capabilities) REQUIRE_CAPS="${2:?--require-capabilities needs ids}"; shift 2 ;;
    # Accepted so existing callers keep working, but a list of SECRET names is
    # no longer a meaningful request from an agent. Point at the replacement
    # rather than silently doing something different from what was asked.
    --require)
      echo "bootstrap_agent_env: --require names secrets; use --require-capabilities" >&2
      echo "  (e.g. --require-capabilities sonar.read_issues,semgrep.appsec_scan)" >&2
      shift 2 ;;
    # An EMPTY value is accepted deliberately and classified as unknown, which
    # denies. Erroring out instead would exit non-zero for the wrong reason and
    # make `--surface ""` look like a broken invocation rather than a refusal.
    --surface) SURFACE="${2?--surface needs an id}"; shift 2 ;;
    -h|--help) sed -n '2,46p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "bootstrap_agent_env: unknown argument '$1'" >&2; exit 2 ;;
  esac
done

# Locked interpreter when present — same rule every other governance entrypoint
# uses, so the capability client runs on the pinned Python.
PY="$GOV_ROOT/.venv/bin/python3"
[ -x "$PY" ] || PY="python3"

CLIENT="$HERE/capability_client.py"
if [ ! -f "$CLIENT" ]; then
  echo "bootstrap_agent_env: missing $CLIENT" >&2
  exit 1
fi

# --- Trust classification ---------------------------------------------------
# One authority for this decision, shared with the Python side. The shell never
# second-guesses it and never carries its own allow-list.
TRUST="$("$PY" -c "
import sys
sys.path.insert(0, '$HERE')
from surface_trust import classify
t = classify('$SURFACE')
print(t.trust_class)
" 2>/dev/null)" || TRUST="model-controlled"
[ -n "$TRUST" ] || TRUST="model-controlled"

# --- Raw export: denied on every model-controlled surface --------------------
if [ "$MODE" = "--export" ]; then
  if [ "$TRUST" != "trusted-operator" ]; then
    echo "DENIED: raw secret export is prohibited on model-controlled surfaces" >&2
    echo "  surface='${SURFACE}' trust='${TRUST}'" >&2
    echo "  Request a named capability instead:" >&2
    echo "    bootstrap_agent_env.sh --check --surface ${SURFACE} --require-capabilities <ids>" >&2
    echo "  Registered capabilities: ops/secrets/capabilities.yaml" >&2
    exit 3
  fi
  # Trusted operator path. hydrate_infisical.py enforces the SAME boundary
  # independently — this is not the only gate, so bypassing the shell buys
  # nothing.
  exec "$PY" "$HERE/hydrate_infisical.py" --surface "$SURFACE" --export "$EXPORT_NAMES"
fi

echo "capability bootstrap: surface=${SURFACE} trust=${TRUST} plane=l9-capability-broker (ops/secrets SSOT)"

if [ -n "$REQUIRE_CAPS" ]; then
  "$PY" "$CLIENT" --check --require "$REQUIRE_CAPS"
else
  "$PY" "$CLIENT" --check
fi
rc=$?

if [ "$rc" -ne 0 ]; then
  # A capability that is not ENABLED is a DELIVERY problem — the broker is
  # unreachable, or this platform issues no session identity the broker can
  # verify. It is never a reason to ask a human to paste a credential into the
  # agent environment; that is the exact posture this file removed.
  echo "capability bootstrap: DEGRADED — capability plane incomplete for surface '${SURFACE}'" >&2
  echo "  configure L9_CAPABILITY_BROKER_URL to a trusted L9 broker, and run that broker" >&2
  echo "  with a workload identity (Kubernetes Auth / SPIFFE / OIDC) to Infisical." >&2
  echo "  Do NOT paste INFISICAL_CLIENT_SECRET, SONAR_TOKEN, SEMGREP_APP_TOKEN or a" >&2
  echo "  Graphiti bearer into this surface — raw secrets are prohibited here." >&2
fi
exit "$rc"
