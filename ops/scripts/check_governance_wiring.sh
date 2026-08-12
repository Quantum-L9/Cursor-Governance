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
warn() { echo "  WARN: $1"; }

resolve_governance_paths_or_exit
GC="$GLOBAL_COMMANDS"
# Prefer the locked project interpreter so Graphiti CLI deps (pydantic, etc.)
# resolve. Bare system python3 often lacks them and must not false-FAIL wiring.
if [ -x "$GC/.venv/bin/python3" ]; then
  GOV_PYTHON="$GC/.venv/bin/python3"
else
  GOV_PYTHON="python3"
fi
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
WS_REAL=$(python3 -c "import os; print(os.path.realpath('$WORKSPACE'))")
GC_REAL=$(python3 -c "import os; print(os.path.realpath('$GC'))")
if [ "$WS_REAL" = "$GC_REAL" ]; then
  # SSOT must not self-alias — .cursor-commands is not required (and must be absent).
  if [ -e "$WORKSPACE/.cursor-commands" ] || [ -L "$WORKSPACE/.cursor-commands" ]; then
    fail "SSOT self-alias present at $WORKSPACE/.cursor-commands (remove; SSOT must not link to itself)"
  else
    pass "SSOT workspace — .cursor-commands self-alias absent"
  fi
elif [ ! -L "$WORKSPACE/.cursor-commands" ]; then
  fail ".cursor-commands missing or not a symlink ($WORKSPACE/.cursor-commands)"
else
  rt=$(python3 -c "import os; print(os.path.realpath('$WORKSPACE/.cursor-commands'))")
  re="$GC_REAL"
  if [ "$rt" = "$re" ]; then
    pass ".cursor-commands -> $re"
  else
    fail ".cursor-commands points to $rt (expected $re / SSOT)"
  fi
fi

# Machine Cursor plans — workspace convenience symlink (not governance SSOT).
mkdir -p "$HOME/.cursor/plans" 2>/dev/null || true
if [ ! -L "$WORKSPACE/.cursor/plans" ]; then
  fail ".cursor/plans missing or not a symlink (expected -> \$HOME/.cursor/plans)"
else
  rt=$(python3 -c "import os; print(os.path.realpath('$WORKSPACE/.cursor/plans'))")
  re=$(python3 -c "import os; print(os.path.realpath('$HOME/.cursor/plans'))")
  if [ "$rt" = "$re" ]; then
    pass ".cursor/plans -> $re"
  else
    fail ".cursor/plans points to $rt (expected $re)"
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
echo "=== SSOT clone freshness ($GC) ==="
SSOT_BRANCH_EXPECTED="${GOVERNANCE_GITHUB_BRANCH:-main}"
if [ ! -d "$GC/.git" ]; then
  fail "SSOT clone missing .git at $GC"
else
  ssot_branch=$(git -C "$GC" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
  if [ "$ssot_branch" = "$SSOT_BRANCH_EXPECTED" ]; then
    pass "SSOT on branch $SSOT_BRANCH_EXPECTED"
  else
    fail "SSOT checked out on '$ssot_branch', expected '$SSOT_BRANCH_EXPECTED' (fix: git -C \"$GC\" checkout $SSOT_BRANCH_EXPECTED)"
  fi

  if git -C "$GC" diff --quiet 2>/dev/null && git -C "$GC" diff --cached --quiet 2>/dev/null; then
    pass "SSOT working tree clean"
  else
    dirty_count=$(git -C "$GC" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    warn "SSOT working tree dirty ($dirty_count file(s)) — commit+push or stash before it silently diverges from GitHub"
  fi

  ahead=$(git -C "$GC" rev-list --count "origin/$SSOT_BRANCH_EXPECTED..HEAD" 2>/dev/null || echo "")
  if [ -z "$ahead" ]; then
    echo "  WARN: no cached origin/$SSOT_BRANCH_EXPECTED ref in SSOT clone — run git -C \"$GC\" fetch origin"
  elif [ "$ahead" -gt 0 ]; then
    fail "SSOT has $ahead unpushed commit(s) ahead of origin/$SSOT_BRANCH_EXPECTED — review before they linger (see git -C \"$GC\" log origin/$SSOT_BRANCH_EXPECTED..HEAD)"
  else
    pass "SSOT has no unpushed commits ahead of origin/$SSOT_BRANCH_EXPECTED (last fetched)"
  fi

  # Tip freshness: HEAD must equal origin/main. Refresh fetch when activate receipt is stale (>900s).
  RECEIPT="$HOME/.cursor/governance-activate.last"
  NEED_FETCH=1
  if [ -f "$RECEIPT" ]; then
    RECEIPT_AGE="$(python3 -c "
import json, time
from pathlib import Path
p = Path('$RECEIPT')
try:
    data = json.loads(p.read_text())
    ts = float(data.get('ts') or data.get('timestamp') or p.stat().st_mtime)
except Exception:
    ts = p.stat().st_mtime
print(int(time.time() - ts))
" 2>/dev/null || echo 99999)"
    if [ "${RECEIPT_AGE:-99999}" -le 900 ]; then
      NEED_FETCH=0
    fi
  fi
  if [ "$NEED_FETCH" -eq 1 ]; then
    git -C "$GC" fetch --quiet origin "$SSOT_BRANCH_EXPECTED" 2>/dev/null || true
  fi
  HEAD_SHA="$(git -C "$GC" rev-parse HEAD 2>/dev/null || echo "")"
  ORIGIN_SHA="$(git -C "$GC" rev-parse "origin/$SSOT_BRANCH_EXPECTED" 2>/dev/null || echo "")"
  if [ -n "$HEAD_SHA" ] && [ -n "$ORIGIN_SHA" ] && [ "$HEAD_SHA" = "$ORIGIN_SHA" ]; then
    pass "SSOT HEAD == origin/$SSOT_BRANCH_EXPECTED (${HEAD_SHA:0:7})"
  elif [ -z "$ORIGIN_SHA" ]; then
    fail "SSOT missing origin/$SSOT_BRANCH_EXPECTED ref — fetch failed or offline (HEAD=${HEAD_SHA:0:7})"
  else
    fail "SSOT HEAD ${HEAD_SHA:0:7} != origin/$SSOT_BRANCH_EXPECTED ${ORIGIN_SHA:0:7} — run governance_activate_fresh.sh"
  fi

  # SSOT must not carry a self-alias even when the checked workspace is a consumer.
  if [ -e "$GC/.cursor-commands" ] || [ -L "$GC/.cursor-commands" ]; then
    fail "SSOT has .cursor-commands self-alias at $GC/.cursor-commands (remove)"
  else
    pass "SSOT has no .cursor-commands self-alias"
  fi
fi

# Dev checkout vs machine SSOT: slash commands resolve via .cursor-commands → SSOT.
# Warn when a non-SSOT Cursor-Governance workspace has drifted command files.
echo ""
echo "=== slash-command clone drift (workspace vs SSOT) ==="
WS_REAL="$(cd "$WORKSPACE" && pwd -P 2>/dev/null || echo "$WORKSPACE")"
GC_REAL="$(cd "$GC" && pwd -P 2>/dev/null || echo "$GC")"
if [ "$WS_REAL" != "$GC_REAL" ] && [ -f "$WORKSPACE/commands/plan.md" ] && [ -f "$GC/commands/plan.md" ]; then
  if cmp -s "$WORKSPACE/commands/plan.md" "$GC/commands/plan.md"; then
    pass "commands/plan.md matches SSOT (slash /plan will see this content)"
  else
    warn "commands/plan.md differs from SSOT — /plan loads .cursor-commands → $GC until merge+activate (or intentional SSOT sync)"
  fi
else
  pass "slash-command drift check skipped (same clone or plan.md absent)"
fi

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
echo "=== Graphiti memory (GLOBAL-001) ==="
GRAPHITI_CLI="$GC/ops/graphiti/graphiti_memory_client.py"
if [ -f "$GRAPHITI_CLI" ]; then
  pass "graphiti_memory_client.py present (interpreter: $GOV_PYTHON)"
  if "$GOV_PYTHON" -c "import yaml; yaml.safe_load(open('$GC/ops/graphiti/group_registry.yaml'))" 2>/dev/null; then
    pass "group_registry.yaml valid"
  else
    fail "group_registry.yaml invalid"
  fi
  if "$GOV_PYTHON" "$GRAPHITI_CLI" resolve >/dev/null 2>&1; then
    pass "graphiti resolve exits 0"
  elif [ "$GOV_PYTHON" = "python3" ] && ! "$GOV_PYTHON" -c "import pydantic" 2>/dev/null; then
    warn "graphiti resolve skipped — project .venv missing (run: make -C \"$GC\" venv)"
  else
    fail "graphiti resolve failed"
  fi
  if [ -f "$HOME/.cursor/graphiti.env" ]; then
    pass "~/.cursor/graphiti.env exists"
  else
    echo "  WARN: ~/.cursor/graphiti.env missing (copy graphiti.env.example)"
  fi
  # The bootstrap hook delegates to the memory orchestrator internally, so either
  # entry in sessionStart satisfies the wiring (setup retires the orchestrator-only entry).
  if grep -qE "session-start-bootstrap|session-start-memory-orchestrator" "$HOOKS_JSON" 2>/dev/null; then
    pass "sessionStart bootstrap/orchestrator registered"
  else
    fail "sessionStart bootstrap not in hooks.json"
  fi
  if grep -q "before-submit-skill-router.py" "$HOOKS_JSON" 2>/dev/null; then
    pass "beforeSubmitPrompt skill router registered"
  else
    fail "beforeSubmitPrompt skill router missing from hooks.json"
  fi
  if [ -x "$HOME/.cursor/hooks/before-submit-skill-router.py" ] || [ -L "$HOME/.cursor/hooks/before-submit-skill-router.py" ]; then
    pass "before-submit-skill-router.py installed under ~/.cursor/hooks"
  else
    fail "before-submit-skill-router.py missing under ~/.cursor/hooks"
  fi
  GATE_LIB="$GC/ops/graphiti/graphiti_gate_lib.py"
  if [ -f "$GATE_LIB" ] && grep -q "gmp:phase_lock" "$GATE_LIB"; then
    pass "GMP gate matcher present in graphiti_gate_lib.py"
  else
    fail "GMP gate matcher missing"
  fi
  if bash "$GC/ops/graphiti/test_gate_e2e_full.sh" >/dev/null 2>&1; then
    pass "graphiti gate E2E full self-test"
  elif bash "$GC/ops/graphiti/test_gate_e2e.sh" >/dev/null 2>&1; then
    pass "graphiti gate E2E self-test (minimal)"
  else
    fail "graphiti gate E2E self-test"
  fi
else
  fail "Graphiti CLI missing: $GRAPHITI_CLI"
fi

if [ -d "$WORKSPACE/memory-bank" ]; then
  echo "  WARN: memory-bank/ still present — deprecated; remove after Graphiti migrate (do not scaffold)"
else
  pass "memory-bank/ absent (retired)"
fi

# IDE profile is a convenience layer, never a gate — warn only, never fail.
if [ ! -x "$GC/ops/scripts/install_ide_profile.sh" ]; then
  echo "  WARN: install_ide_profile.sh missing — IDE profile not managed"
elif [ -f "$WORKSPACE/.vscode/.l9-ide-desired-hash" ]; then
  pass "IDE profile applied ($(python3 -c '
import json,sys
print(json.load(open(sys.argv[1])).get("class", "unknown"))' "$WORKSPACE/.vscode/.l9-ide-desired-hash" 2>/dev/null || echo unknown))"
else
  echo "  WARN: IDE profile not yet applied — run: bash \"\$HOME/.cursor-governance/ops/scripts/install_ide_profile.sh\" \"$WORKSPACE\""
fi

echo ""
if [ $FAIL -eq 0 ]; then
  echo "RESULT: PASS — governance wiring + sessionEnd hook active"
  exit 0
fi

echo "RESULT: FAIL — run /wire governance"
exit 1

if [ -f "$WORKSPACE/environment/agents/PEER_RUNTIME_BINDINGS.yaml" ] || [ -f "$GC/environment/agents/PEER_RUNTIME_BINDINGS.yaml" ]; then
  pass "peer runtime bindings present"
else
  echo "  WARN: PEER_RUNTIME_BINDINGS.yaml absent in workspace/SSOT"
fi
if [ -f "$WORKSPACE/environment/agents/deployment/reconcile.py" ] || [ -f "$GC/environment/agents/deployment/reconcile.py" ]; then
  pass "deployment reconciler present"
fi
if [ -f "$WORKSPACE/environment/agents/results/gateway.py" ] || [ -f "$GC/environment/agents/results/gateway.py" ]; then
  pass "result gateway present"
fi
if [ -f "$WORKSPACE/environment/agents/generated-data/ingress/ingest.py" ] || [ -f "$GC/environment/agents/generated-data/ingress/ingest.py" ]; then
  pass "generated-data ingress present"
fi
