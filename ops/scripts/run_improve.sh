#!/usr/bin/env bash
# PUBLIC make improve — L4 begin / authorize only.
# Tree kernels are NOT an L4 phase. They fire as the first step of
# make precommit-repo (ops/autonomy/kernel_gate.py). Two-step:
#   make improve                 → begin (if needed)
#   make improve IMPROVE_RECORD=1 → authorize-release (no kernel stamp)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"
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
    echo "      Run make improve first, then make improve IMPROVE_RECORD=1" >&2
    echo "      to authorize-release. Kernels fire in make precommit-repo." >&2
    exit 1
  fi
  echo "--- make improve: authorize-release (phase=$phase; kernels are not L4) ---"
  _l4 authorize-release
  echo "RESULT: PASS — L4 release authorized. Next: make pr (kernel hook then checks once)"
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
  1. Authorize when the local program is finished: make improve IMPROVE_RECORD=1
  2. Publish once: PR_REMEDIATE=0 make pr
  3. The first step of precommit-repo is ops/autonomy/kernel_gate.py.
     If it fails, apply Recursive Alignment then Validate & Repair, commit,
     run kernel_gate.py record, and re-run the same make pr. Hooks and tests
     fire once after that hook passes.
Do not treat L4 record-kernels as the kernel apply path.
=== END L9_AGENT_REQUIRED ===

RESULT: PASS — improve phase ready (authorize, then make pr)
EOF
