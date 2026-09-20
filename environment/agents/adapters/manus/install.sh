#!/usr/bin/env bash
# Manus adapter installer — native Infisical connector readiness check.
#
# This script validates the committed Manus carrier and the caller's actual Git
# workspace. The connector's Universal Auth fields belong only in Manus Custom
# MCP encrypted configuration. This installer never inherits Cursor SessionStart
# behavior, resolves a secret, or writes a credential into the workspace.
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

VALIDATOR="$GOVERNANCE/environment/agents/adapters/manus/validate_manus_adapter.py"
[ -f "$VALIDATOR" ] || fail "missing adapter validator at $VALIDATOR"
PYTHON_BIN="$GOVERNANCE/.venv/bin/python"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="python3"

say "manus-install: validating native Infisical connector for workspace=$WORKSPACE"
"$PYTHON_BIN" "$VALIDATOR" --repo-root "$GOVERNANCE" || fail "native adapter validation failed"

if [ "$CHECK" = "1" ]; then
  say "manus-install: CHECKED (native connector carrier only)"
else
  say "manus-install: READY (configure the l9-manus-infisical Custom MCP separately)"
fi
