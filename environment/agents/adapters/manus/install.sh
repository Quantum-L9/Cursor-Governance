#!/usr/bin/env bash
# Manus adapter installer — thin surface binding over the shared bootstrap.
#
# Vendor-neutral readiness, secret posture, repository identity, and autonomy
# gates stay in ops/. This script only selects the Manus surface and validates
# that an actual git workspace was supplied. It cannot install Manus project
# instructions or create a remote MCP transport; those are explicit platform
# configuration concerns documented in setup.md.
#
# Manus exposes no SessionStart hook, so this installer is the session start.
# Beyond the shared bootstrap it makes the two machine-level bindings every
# later gate assumes (session_env.sh: the $HOME/.cursor-governance SSOT path and
# the declared surface) and provisions the governance-managed authority
# checkout the default projection binding verifies. `--check` reports those
# without mutating them.
#
# Usage:
#   install.sh [--governance <dir>] [--workspace <dir>] [--check] [--quiet]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_GOVERNANCE="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
GOVERNANCE="$DEFAULT_GOVERNANCE"
WORKSPACE="$PWD"
CHECK=0
QUIET=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --governance) GOVERNANCE="${2:?--governance needs a path}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?--workspace needs a path}"; shift 2 ;;
    --check) CHECK=1; shift ;;
    --quiet) QUIET=1; shift ;;
    -h|--help)
      sed -n '1,11p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *)
      printf 'manus-install: unknown argument %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

# Declare the surface for every child, not only for the bootstrap's --surface
# argument: helpers the bootstrap calls read the variable, and an unset value
# fails closed to Cursor in is_cursor_host_surface().
export L9_GOVERNANCE_SURFACE=manus

say() {
  [ "$QUIET" = "1" ] || printf '%s\n' "$*" >&2
}

fail() {
  printf 'manus-install ERROR: %s\n' "$*" >&2
  exit 1
}

WORKSPACE="$(cd "$WORKSPACE" 2>/dev/null && pwd -P)" || fail "workspace does not exist"
HOME_REAL="$(cd "$HOME" 2>/dev/null && pwd -P)"
if [ "$WORKSPACE" = "$HOME_REAL" ]; then
  fail "refusing --workspace \$HOME ($WORKSPACE); pass a repository root"
fi
if ! git -C "$WORKSPACE" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "refusing --workspace $WORKSPACE; not a git work tree"
fi
GOVERNANCE="$(cd "$GOVERNANCE" 2>/dev/null && pwd -P)" || fail "governance directory does not exist"
[ -f "$GOVERNANCE/CANONICAL_LAW.md" ] || fail "no governance SSOT at $GOVERNANCE"

BOOTSTRAP="$GOVERNANCE/ops/scripts/bootstrap_agent_environment.sh"
[ -f "$BOOTSTRAP" ] || fail "missing shared bootstrap at $BOOTSTRAP"
VALIDATOR="$GOVERNANCE/environment/agents/adapters/manus/validate_manus_adapter.py"

ARGS=(--surface manus --governance "$GOVERNANCE" --workspace "$WORKSPACE")
[ "$CHECK" = "1" ] && ARGS+=(--check)
[ "$QUIET" = "1" ] && ARGS+=(--quiet)

# The SSOT path and the declared surface must exist before the bootstrap, not
# after it: the bootstrap's own helpers resolve governance through them.
SESSION_ENV="$GOVERNANCE/environment/agents/adapters/manus/session_env.sh"
if [ -f "$SESSION_ENV" ]; then
  SESSION_ARGS=(--governance "$GOVERNANCE")
  [ "$CHECK" = "1" ] && SESSION_ARGS+=(--check)
  [ "$QUIET" = "1" ] && SESSION_ARGS+=(--quiet)
  bash "$SESSION_ENV" "${SESSION_ARGS[@]}" || true
else
  say "manus-install: session_env.sh absent (SSOT path and surface not bound)"
fi

say "manus-install: shared bootstrap for workspace=$WORKSPACE"
bash "$BOOTSTRAP" "${ARGS[@]}"
status=$?
case "$status" in
  0|6) ;;
  *) say "manus-install: BLOCKED (shared bootstrap exit $status)"; exit "$status" ;;
esac
[ -f "$VALIDATOR" ] || fail "missing adapter validator at $VALIDATOR"
PYTHON_BIN="$GOVERNANCE/.venv/bin/python3"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$GOVERNANCE/.venv/bin/python"
[ -x "$PYTHON_BIN" ] || fail "locked interpreter absent after bootstrap"
export PYTHONDONTWRITEBYTECODE=1
"$PYTHON_BIN" -B -I -c '
import sys
from pathlib import Path
assert Path(sys.prefix).resolve() == Path(sys.argv[1]).resolve(), "wrong venv prefix"
assert sys.prefix != sys.base_prefix, "not a virtual environment"
import yaml
' "$GOVERNANCE/.venv" 2>/dev/null || fail "locked validator interpreter prefix/yaml verification failed"
"$PYTHON_BIN" -B "$VALIDATOR" --repo-root "$GOVERNANCE" >&2 || fail "native adapter validation failed"

# The Manus host has no SessionStart hook, so this installer IS the session
# start path: bind the default projections here, exactly as the Cursor hook and
# the Claude Code hook do for their surfaces. `autobind` in the contract means
# "no skill gates it", not "the host fires a hook".
# The binding verifies the governance-managed authority checkout. Cursor's
# SessionStart provisions it in session_start_bootstrap.sh; Manus has no hook,
# so the installer does it here. The provisioner is fail-open and exits 0, and
# it never touches an operator-chosen L9_AUTHORITY_ROOT.
AUTHORITY="$GOVERNANCE/ops/scripts/ensure_authority_checkout.sh"
if [ "$CHECK" != "1" ] && [ -f "$AUTHORITY" ]; then
  bash "$AUTHORITY" >&2 || true
fi
BINDING="$GOVERNANCE/ops/autonomy/host_binding.py"
if [ -f "$BINDING" ]; then
  BIND_STATUS="$(
    "$PYTHON_BIN" -B "$BINDING" --host manus --workspace "$WORKSPACE" --format json 2>/dev/null \
      | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("status","UNKNOWN"))' 2>/dev/null \
      || echo UNKNOWN
  )"
  say "manus-install: default projection binding (manus) — $BIND_STATUS"
  "$PYTHON_BIN" -B "$BINDING" --host manus --workspace "$WORKSPACE" --format line >&2 || true
  if [ "$BIND_STATUS" != "BOUND" ]; then
    # Fail-open like every other host: the session continues, unbound, and may
    # cite no operating-plane semantics. It is reported, never invented.
    #
    # The exit code is deliberately NOT escalated. This script's status is the
    # shared bootstrap's posture; `make manus-start` is the enforcement point
    # for the projection binding. Two meanings in one code would leave a
    # consumer unable to tell "bootstrap degraded" from "binding rejected".
    say "manus-install: binding $BIND_STATUS (reported; 'make manus-start' enforces)"
  fi
else
  say "manus-install: binding control absent (reported; cite no operating-plane semantics)"
fi

case "$status" in
  0) say "manus-install: READY (shared bootstrap)" ;;
  6) say "manus-install: DEGRADED (shared bootstrap; session remains usable)" ;;
  *) say "manus-install: BLOCKED (shared bootstrap exit $status)" ;;
esac
exit "$status"
