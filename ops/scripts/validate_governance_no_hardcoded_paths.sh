#!/usr/bin/env bash
# Enforce CANONICAL_LAW §9 — no machine-specific paths in governance wiring scripts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"

resolve_governance_paths_or_exit

FAIL=0

SCAN_FILES=(
  "$GLOBAL_COMMANDS/ops/hooks/session_end_governance_backup.sh"
  "$GLOBAL_COMMANDS/ops/scripts/resolve_governance_paths.sh"
  "$GLOBAL_COMMANDS/ops/scripts/backup_to_github.sh"
  "$GLOBAL_COMMANDS/ops/scripts/setup_workspace_symlinks.sh"
  "$GLOBAL_COMMANDS/ops/scripts/validate_governance_symlinks.sh"
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
echo "  GlobalCommands: $GLOBAL_COMMANDS"
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
  echo "RESULT: PASS — wiring kernel resolves via resolve_governance_paths.sh (~/.cursor-governance SSOT)"
  exit 0
fi

echo "RESULT: FAIL — resolve via resolve_governance_paths.sh (~/.cursor-governance, Dropbox fallback); see CANONICAL_LAW §9"
exit 1
