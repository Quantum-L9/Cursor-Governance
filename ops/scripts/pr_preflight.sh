#!/usr/bin/env bash
# INTERNAL make pr-preflight — read-only publish predicates. No L4 mutation.
# Fail-fast: detached HEAD / main|master / no commits ahead / L4 check-remote denied.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"
GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WS="${WS:-${1:-$(pwd)}}"
WS="$(cd "$WS" && pwd)"
PR_BASE="${PR_BASE:-origin/main}"

cd "$WS"

if [[ -x "$GOV_ROOT/.venv/bin/python" ]]; then
  PY="$GOV_ROOT/.venv/bin/python"
  export PATH="$GOV_ROOT/.venv/bin:$PATH"
else
  PY="$(command -v python3)"
fi

echo "=== pr-preflight (INTERNAL; read-only) ==="

branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$branch" == "HEAD" ]]; then
  echo "FAIL: detached HEAD — check out a feature branch before make pr" >&2
  exit 1
fi
if [[ "$branch" == "main" || "$branch" == "master" ]]; then
  echo "FAIL: on '$branch' — create/checkout a feature branch, then make improve" >&2
  exit 1
fi

if ! git rev-parse --verify "$PR_BASE" >/dev/null 2>&1; then
  echo "FAIL: missing base ref $PR_BASE (fetch or set PR_BASE)" >&2
  exit 1
fi

ahead="$(git rev-list --count "${PR_BASE}..HEAD" 2>/dev/null || echo 0)"
if [[ "${ahead:-0}" -eq 0 ]]; then
  echo "FAIL: no commits on '$branch' ahead of $PR_BASE — commit first, then make improve" >&2
  exit 1
fi

L4_CLI="$GOV_ROOT/ops/autonomy/l4_local.py"
if [[ -f "$L4_CLI" && "${L9_L4_LOCAL_AUTONOMY:-1}" != "0" ]]; then
  if ! "$PY" "$L4_CLI" --workspace "$WS" check-remote; then
    echo "FAIL: L4 release not authorized — run make improve, apply kernels," >&2
    echo "      then: make improve IMPROVE_RECORD=1" >&2
    exit 1
  fi
fi

echo "OK: pr-preflight (branch=$branch ahead=$ahead base=$PR_BASE)"
