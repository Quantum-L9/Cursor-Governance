#!/usr/bin/env bash
# Manus adapter installer — thin surface binding over the shared bootstrap.
#
# Vendor-neutral readiness, secret posture, repository identity, and autonomy
# gates stay in ops/. This script only selects the Manus surface and validates
# that an actual git workspace was supplied. It cannot install Manus project
# instructions or create a remote MCP transport; those are explicit platform
# configuration concerns documented in setup.md.
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

ARGS=(--surface manus --governance "$GOVERNANCE" --workspace "$WORKSPACE")
[ "$CHECK" = "1" ] && ARGS+=(--check)
[ "$QUIET" = "1" ] && ARGS+=(--quiet)

say "manus-install: shared bootstrap for workspace=$WORKSPACE"
bash "$BOOTSTRAP" "${ARGS[@]}"
status=$?
case "$status" in
  0) say "manus-install: READY (shared bootstrap)" ;;
  6) say "manus-install: DEGRADED (shared bootstrap; session remains usable)" ;;
  *) say "manus-install: BLOCKED (shared bootstrap exit $status)" ;;
esac
exit "$status"
