#!/usr/bin/env bash
# PUBLIC make improve — L4 begin / authorize only.
# Tree kernels must be recorded before IMPROVE_RECORD=1:
#   make improve                 → begin (if needed)
#   python3 ops/autonomy/kernel_gate.py record
#   make improve IMPROVE_RECORD=1 → authorize-release (fails closed without receipt)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"
# rules/06: sourcing alone does not bind which clone is authoritative, and the
# EXIT trap warns when the entry point never ran. This script then pins GOV_ROOT
# to its OWN checkout on the next line — `make improve` must drive the tree it
# was invoked from — so the resolver is called for its binding and side effects
# (session env via l9_load_session_env) and is not allowed to fail the run.
resolve_governance_paths || true
GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WS="${WS:-$(pwd)}"
WS="$(cd "$WS" && pwd)"
PR_BASE="${PR_BASE:-origin/main}"
IMPROVE_RECORD="${IMPROVE_RECORD:-0}"

cd "$WS"

if [[ -x "$GOV_ROOT/.venv/bin/python" ]]; then
  PY="$GOV_ROOT/.venv/bin/python"
else
  PY="$(command -v python3)"
fi
L4_CLI="$GOV_ROOT/ops/autonomy/l4_local.py"
if [[ ! -f "$L4_CLI" ]]; then
  echo "FAIL: missing $L4_CLI" >&2
  exit 1
fi

_l4() {
  "$PY" "$L4_CLI" --workspace "$WS" "$@"
}

_phase() {
  _l4 status | "$PY" -c 'import json,sys; print((json.load(sys.stdin).get("phase") or "") or "")'
}

if [[ "$IMPROVE_RECORD" = "1" ]]; then
  phase="$(_phase)"
  if [[ "$phase" != "executing" && "$phase" != "kernels_recorded" ]]; then
    echo "FAIL: IMPROVE_RECORD refused — phase is '${phase:-none}'." >&2
    echo "      Run make improve first, record tree kernels, then" >&2
    echo "      make improve IMPROVE_RECORD=1 to authorize-release." >&2
    exit 1
  fi
  echo "--- make improve: authorize-release (phase=$phase; requires kernel_gate receipt) ---"
  _l4 authorize-release
  echo "RESULT: PASS — L4 release authorized. Next: PR_REMEDIATE=0 make pr"
  exit 0
fi

phase="$(_phase)"
if [[ -z "$phase" ]]; then
  echo "--- make improve: l4-begin ---"
  _l4 begin ${CONTRACT_ID:+--contract-id "$CONTRACT_ID"} ${PR_BASE:+--base "$PR_BASE"}
  phase="executing"
elif [[ "$phase" = "release_authorized" ]]; then
  echo "OK: L4 already release_authorized — no begin."
fi

cat <<EOF

=== L9_AGENT_REQUIRED ===
ACTION: authorize_then_precommit
SKILL: L4 authorize + kernel_gate precommit hook
COMMAND: make improve
PHASE: ${phase}
WORKSPACE: ${WS}
PR_BASE: ${PR_BASE}
INSTRUCTIONS:
  1. Apply kernels/Recursive Alignment.md then kernels/Validate & Repair.md
  2. python3 ops/autonomy/kernel_gate.py record
  3. Authorize: make improve IMPROVE_RECORD=1
  4. Publish once: PR_REMEDIATE=0 make pr
Do not authorize before the kernel receipt exists.
=== END L9_AGENT_REQUIRED ===

RESULT: PASS — improve phase ready (authorize, then make pr)
EOF
