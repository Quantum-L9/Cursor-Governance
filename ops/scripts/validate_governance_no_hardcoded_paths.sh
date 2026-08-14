#!/usr/bin/env bash
# Enforce CANONICAL_LAW §9 — no machine-specific paths in governance wiring scripts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Scan the checkout this script ships in, not $HOME/.cursor-governance. Resolving a
# machine-level SSOT clone made the validator unrunnable on a CI runner (no such clone
# exists there, and resolve_governance_paths_or_exit hard-exits 1), and made a local run
# from a worktree validate a different tree than the one under test. Override with
# GOVERNANCE_SCAN_ROOT to point at another clone deliberately.
GOVERNANCE_SCAN_ROOT="${GOVERNANCE_SCAN_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

FAIL=0

SCAN_FILES=(
  "$GOVERNANCE_SCAN_ROOT/ops/hooks/session_end_governance_backup.sh"
  "$GOVERNANCE_SCAN_ROOT/ops/scripts/resolve_governance_paths.sh"
  "$GOVERNANCE_SCAN_ROOT/ops/scripts/backup_to_github.sh"
  "$GOVERNANCE_SCAN_ROOT/ops/scripts/setup_workspace_symlinks.sh"
  "$GOVERNANCE_SCAN_ROOT/ops/scripts/validate_governance_symlinks.sh"
  "$GOVERNANCE_SCAN_ROOT/ops/scripts/install_ide_profile.sh"
  "$GOVERNANCE_SCAN_ROOT/ops/scripts/backup_gate.sh"
)

pass() { echo "  OK: $1"; }
fail() { echo "  FAIL: $1"; FAIL=1; }

scan_file() {
  local f=$1
  local patterns=('/Users/' '/home/' 'Library/CloudStorage/Dropbox')
  local p line lineno rest stripped
  for p in "${patterns[@]}"; do
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      lineno="${line%%:*}"
      rest="${line#*:}"
      stripped="${rest#"${rest%%[![:space:]]*}"}"
      [[ "$stripped" =~ ^# ]] && continue
      [[ "$rest" == *'$HOME'* ]] && continue
      fail "$f:$lineno:${rest#*:}"
    done < <(grep -Fn "$p" "$f" 2>/dev/null || true)
  done
}

echo "=== Governance path contract (CANONICAL_LAW §9) ==="
echo "  Scan root: $GOVERNANCE_SCAN_ROOT"
echo "  Scope: governance wiring kernel (ops/hooks + path resolvers)"
echo ""

for f in "${SCAN_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    fail "missing wiring script: $f"
    continue
  fi
  pass "scanning: $(basename "$f")"
  scan_file "$f"
done

echo ""
if [ $FAIL -eq 0 ]; then
  echo "RESULT: PASS — wiring kernel in $GOVERNANCE_SCAN_ROOT resolves paths dynamically"
  exit 0
fi

echo "RESULT: FAIL — resolve via resolve_governance_paths.sh (~/.cursor-governance only; Dropbox is not a fallback); see CANONICAL_LAW"
exit 1
