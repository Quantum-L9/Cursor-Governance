#!/usr/bin/env bash
# Validate Cursor governance symlinks — CANONICAL_LAW enforcement
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"

FAIL=0
pass() { echo "  OK: $1"; }
fail() { echo "  FAIL: $1"; FAIL=1; }
warn() { echo "  WARN: $1"; }

resolve_governance_paths_or_exit
GC="$GLOBAL_COMMANDS"
WORKSPACE="${1:-$(pwd)}"

link_check() {
  local link=$1 expected=$2 label=$3
  if [ ! -L "$link" ]; then
    fail "$label: not a symlink ($link)"
    return
  fi
  local rt re
  rt=$(python3 -c "import os; print(os.path.realpath('$link'))")
  re=$(python3 -c "import os; print(os.path.realpath('$expected'))")
  if [ "$rt" = "$re" ]; then
    pass "$label -> $re"
  else
    fail "$label: expected $re got $rt"
  fi
}

echo "=== Canonical paths ==="
echo "  Governance root: $GOV_ROOT"
echo "  GlobalCommands:  $GC"
echo "  Workspace:       $WORKSPACE"
echo ""

echo "=== Dropbox SSOT ==="
for d in "$GC" "$GC/commands" "$GC/skills" "$GC/rules" "$GOV_ROOT/CANONICAL_LAW.md"; do
  [ -e "$d" ] && pass "exists: $d" || fail "missing: $d"
done

echo ""
echo "=== User-level Cursor ==="
link_check "$HOME/.cursor/skills" "$GC/skills" "~/.cursor/skills"
link_check "$HOME/.cursor/commands" "$GC/commands" "~/.cursor/commands"

echo ""
echo "=== Repo: ONE GlobalCommands entry ==="
link_check "$WORKSPACE/.cursor-commands" "$GC" ".cursor-commands"

if [ -e "$WORKSPACE/.cursor/governance/GlobalCommands" ]; then
  fail ".cursor/governance/GlobalCommands must not exist (use .cursor-commands only)"
else
  pass "no .cursor/governance/GlobalCommands"
fi

if [ -L "$WORKSPACE/.cursor/governance" ]; then
  fail ".cursor/governance must be a local directory, not a symlink to Dropbox root"
elif [ -d "$WORKSPACE/.cursor/governance" ]; then
  pass ".cursor/governance/ is local directory"
  link_check "$WORKSPACE/.cursor/governance/CANONICAL_LAW.md" "$GOV_ROOT/CANONICAL_LAW.md" "CANONICAL_LAW.md"
else
  fail ".cursor/governance/ missing (run setup_workspace_symlinks.sh)"
fi

echo ""
echo "=== Repo .cursor/ anti-duplication ==="
for forbidden in "$WORKSPACE/.cursor/commands" "$WORKSPACE/.cursor/skills"; do
  if [ -e "$forbidden" ]; then
    fail "forbidden: $forbidden"
  else
    pass "absent: $(basename "$forbidden")"
  fi
done

if [ -d "$WORKSPACE/.cursor/rules" ]; then
  pass ".cursor/rules/ (repo overlay)"
fi

echo ""
echo "=== Path contract (CANONICAL_LAW §9) ==="
if bash "$SCRIPT_DIR/validate_governance_no_hardcoded_paths.sh"; then
  pass "no hardcoded machine paths in ops/hooks/rules"
else
  fail "hardcoded machine paths detected — run validate_governance_no_hardcoded_paths.sh"
fi

echo ""
echo "=== L9 skills (.cursor-commands/skills) ==="
for s in l9-structured-reasoning l9-skill-compiler l9-wire-skill-into-repo l9-create-skill l9-update-agent-docs l9-gmp-protocol; do
  [ -f "$GC/skills/$s/SKILL.md" ] && pass "$s" || fail "missing $s"
done

echo ""
if [ $FAIL -eq 0 ]; then
  echo "RESULT: PASS — GlobalCommands only via .cursor-commands"
  exit 0
else
  echo "RESULT: FAIL"
  exit 1
fi
