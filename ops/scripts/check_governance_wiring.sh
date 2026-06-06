#!/usr/bin/env bash
# Verify repo governance symlinks + sessionEnd backup hook.
# Exit 0 = PASS. Exit 1 = FAIL (run /wire governance).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"

WORKSPACE="${1:-$(pwd)}"
FAIL=0

pass() { echo "  OK: $1"; }
fail() { echo "  FAIL: $1"; FAIL=1; }

resolve_governance_paths_or_exit
GC="$GLOBAL_COMMANDS"
HOOK_SRC="$GC/ops/hooks/session_end_governance_backup.sh"
HOOK_LINK="$HOME/.cursor/hooks/governance-backup.sh"
HOOKS_JSON="$HOME/.cursor/hooks.json"
EXPECTED_CMD="./hooks/governance-backup.sh"

echo "=== Governance wiring check ==="
echo "  Governance root: $GOV_ROOT"
echo "  GlobalCommands:  $GC"
echo "  Workspace:       $WORKSPACE"
echo ""

echo "=== Repo symlinks ==="
if [ ! -L "$WORKSPACE/.cursor-commands" ]; then
  fail ".cursor-commands missing or not a symlink ($WORKSPACE/.cursor-commands)"
else
  rt=$(python3 -c "import os; print(os.path.realpath('$WORKSPACE/.cursor-commands'))")
  re=$(python3 -c "import os; print(os.path.realpath('$GC'))")
  if [ "$rt" = "$re" ]; then
    pass ".cursor-commands -> $re"
  else
    fail ".cursor-commands points to $rt (expected $re)"
  fi
fi

if [ -e "$WORKSPACE/.cursor/governance/GlobalCommands" ]; then
  fail ".cursor/governance/GlobalCommands must not exist"
else
  pass "no .cursor/governance/GlobalCommands"
fi

if [ -L "$WORKSPACE/.cursor/governance" ]; then
  fail ".cursor/governance must be a local directory, not a symlink"
elif [ -d "$WORKSPACE/.cursor/governance" ]; then
  law="$WORKSPACE/.cursor/governance/CANONICAL_LAW.md"
  if [ -L "$law" ]; then
    rt=$(python3 -c "import os; print(os.path.realpath('$law'))")
    re=$(python3 -c "import os; print(os.path.realpath('$GOV_ROOT/CANONICAL_LAW.md'))")
    if [ "$rt" = "$re" ]; then
      pass "CANONICAL_LAW.md -> $re"
    else
      fail "CANONICAL_LAW.md points to $rt (expected $re)"
    fi
  else
    fail ".cursor/governance/CANONICAL_LAW.md missing or not a symlink"
  fi
else
  fail ".cursor/governance/ missing (run /wire governance)"
fi

for forbidden in "$WORKSPACE/.cursor/commands" "$WORKSPACE/.cursor/skills"; do
  if [ -e "$forbidden" ]; then
    fail "forbidden duplicate: $forbidden"
  else
    pass "absent: $(basename "$forbidden")"
  fi
done

echo ""
echo "=== sessionEnd governance backup hook ==="
if [ ! -f "$HOOK_SRC" ]; then
  fail "hook script missing: $HOOK_SRC"
elif [ ! -x "$HOOK_SRC" ]; then
  fail "hook script not executable: $HOOK_SRC"
else
  pass "hook script exists: $HOOK_SRC"
fi

if [ ! -L "$HOOK_LINK" ]; then
  fail "hook symlink missing: $HOOK_LINK"
else
  rt=$(python3 -c "import os; print(os.path.realpath('$HOOK_LINK'))")
  re=$(python3 -c "import os; print(os.path.realpath('$HOOK_SRC'))")
  if [ "$rt" = "$re" ]; then
    pass "hook symlink -> $re"
  else
    fail "hook symlink points to $rt (expected $re)"
  fi
fi

if [ ! -f "$HOOKS_JSON" ]; then
  fail "hooks.json missing: $HOOKS_JSON"
else
  if python3 - "$HOOKS_JSON" "$EXPECTED_CMD" <<'PY'
import json
import sys
from pathlib import Path

hooks_json = Path(sys.argv[1])
expected = sys.argv[2]
data = json.loads(hooks_json.read_text())
entries = data.get("hooks", {}).get("sessionEnd", [])
ok = any(isinstance(e, dict) and e.get("command") == expected for e in entries)
sys.exit(0 if ok else 1)
PY
  then
    pass "sessionEnd hook registered in $HOOKS_JSON"
  else
    fail "sessionEnd hook not registered (expected command: $EXPECTED_CMD)"
  fi
fi

echo ""
if [ $FAIL -eq 0 ]; then
  echo "RESULT: PASS — governance wiring + sessionEnd hook active"
  exit 0
fi

echo "RESULT: FAIL — run /wire governance"
exit 1
