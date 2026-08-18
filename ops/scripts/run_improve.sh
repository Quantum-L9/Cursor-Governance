#!/usr/bin/env bash
# PUBLIC make improve — compose existing L4 wrappers (begin / record-kernels / authorize).
# Does not apply markdown kernels itself. Two-step:
#   make improve                 → begin (if needed) + emit kernel instructions
#   make improve IMPROVE_RECORD=1 → record-kernels + authorize-release (no rubber-stamp)
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
    echo "      Run make improve first, apply kernels/Recursive Alignment.md" >&2
    echo "      then kernels/Validate & Repair.md, commit revisions, then:" >&2
    echo "      make improve IMPROVE_RECORD=1" >&2
    exit 1
  fi
  echo "--- make improve: record-kernels + authorize-release (phase=$phase) ---"
  _l4 record-kernels
  _l4 authorize-release
  echo "RESULT: PASS — L4 release authorized. Next: make pr-check then make pr"
  exit 0
fi

phase="$(_phase)"
if [[ -z "$phase" ]]; then
  echo "--- make improve: l4-begin ---"
  _l4 begin ${CONTRACT_ID:+--contract-id "$CONTRACT_ID"} ${PR_BASE:+--base "$PR_BASE"}
  phase="executing"
elif [[ "$phase" = "release_authorized" ]]; then
  echo "OK: L4 already release_authorized — no begin. Re-run kernels if the tree changed,"
  echo "    then make improve IMPROVE_RECORD=1 to refresh the receipt."
fi

cat <<EOF

=== L9_AGENT_REQUIRED ===
ACTION: apply_kernels_revision_pass
SKILL: kernels (Recursive Alignment + Validate & Repair)
COMMAND: make improve
PHASE: ${phase}
WORKSPACE: ${WS}
PR_BASE: ${PR_BASE}
INSTRUCTIONS:
  1. Apply kernels/Recursive Alignment.md to the diff vs ${PR_BASE}
  2. Apply kernels/Validate & Repair.md to the finished local tree
  3. Commit any revisions on this stacked branch (no push)
  4. Record and authorize: make improve IMPROVE_RECORD=1
  5. Quality gate: make pr-check
  6. Publish once: make pr
Do not treat record-kernels as a substitute for applying the kernels.
=== END L9_AGENT_REQUIRED ===

RESULT: PASS — improve phase ready (apply kernels, then IMPROVE_RECORD=1)
EOF
