#!/usr/bin/env bash
# Verify consumer repo symlinks (--workspace) and machine sessionEnd/Graphiti
# (--machine). Default is both. ssot / ssot_checkout skip consumer-link
# requirements. Empty $HOME/.l9 isolates (no identity files) skip --workspace.
# Exit 0 = PASS. Exit 1 = FAIL with a class-specific RESULT line.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"

CHECK_WORKSPACE=0
CHECK_MACHINE=0
POSITIONAL=()
for arg in "$@"; do
  case "$arg" in
    --workspace) CHECK_WORKSPACE=1 ;;
    --machine) CHECK_MACHINE=1 ;;
    --*)
      echo "ERROR: unknown flag $arg (expected --workspace and/or --machine)" >&2
      exit 2
      ;;
    *) POSITIONAL+=("$arg") ;;
  esac
done
if [ "$CHECK_WORKSPACE" -eq 0 ] && [ "$CHECK_MACHINE" -eq 0 ]; then
  CHECK_WORKSPACE=1
  CHECK_MACHINE=1
fi
WORKSPACE="${POSITIONAL[0]:-$(pwd)}"
FAIL=0
FAIL_CONSUMER=0
FAIL_SESSIONEND=0
FAIL_GRAPHITI=0
CURRENT_FAIL_CLASS=wiring

WARN_FILE="$(mktemp)"
trap 'rm -f "$WARN_FILE"' EXIT

pass() { echo "  OK: $1"; }
fail() {
  echo "  FAIL: $1"
  FAIL=1
  case "$CURRENT_FAIL_CLASS" in
    consumer) FAIL_CONSUMER=1 ;;
    sessionend) FAIL_SESSIONEND=1 ;;
    graphiti) FAIL_GRAPHITI=1 ;;
  esac
}
warn() { echo "$1" >> "$WARN_FILE"; }

emit_result() {
  echo ""
  if [ "$FAIL" -eq 0 ]; then
    echo "RESULT: PASS — governance wiring"
  else
    if [ "$FAIL_CONSUMER" -eq 1 ]; then
      echo "RESULT: FAIL — consumer workspace wiring"
    fi
    if [ "$FAIL_SESSIONEND" -eq 1 ]; then
      echo "RESULT: FAIL — sessionEnd hook incomplete"
    fi
    if [ "$FAIL_GRAPHITI" -eq 1 ]; then
      echo "RESULT: FAIL — Graphiti wiring"
    fi
    if [ "$FAIL_CONSUMER" -eq 0 ] && [ "$FAIL_SESSIONEND" -eq 0 ] && [ "$FAIL_GRAPHITI" -eq 0 ]; then
      echo "RESULT: FAIL — governance wiring"
    fi
  fi
  if [ -s "$WARN_FILE" ]; then
    echo ""
    echo "=== non-blocking ==="
    while IFS= read -r w; do
      echo "  WARN: $w"
    done < "$WARN_FILE"
  fi
}

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

WS_KIND="$(classify_workspace_kind "$WORKSPACE")"

echo "=== Governance wiring check ==="
echo "  Governance root: $GOV_ROOT"
echo "  GlobalCommands:  $GC"
echo "  Workspace:       $WORKSPACE"
echo "  Workspace kind:  $WS_KIND"
echo ""

# Empty $HOME/.l9 isolates (no identity files) are not consumer workspaces.
# ssot_checkout (identity tree, including gov worktrees) keeps workspace checks
# with consumer-link requirements relaxed.
if is_l9_isolate_workspace "$WORKSPACE" && [ "$WS_KIND" != "ssot_checkout" ] && [ "$WS_KIND" != "ssot" ]; then
  if [ "$CHECK_WORKSPACE" -eq 1 ]; then
    echo "OK: skip consumer workspace wiring (isolate under \$HOME/.l9)"
  fi
  CHECK_WORKSPACE=0
fi

if [ "$CHECK_WORKSPACE" -eq 1 ]; then
CURRENT_FAIL_CLASS=consumer
echo "=== Repo symlinks ==="
WS_REAL=$(python3 -c "import os; print(os.path.realpath('$WORKSPACE'))")
GC_REAL=$(python3 -c "import os; print(os.path.realpath('$GC'))")
if [ "$WS_KIND" = "ssot" ]; then
  # SSOT must not self-alias — .cursor-commands is not required (and must be absent).
  if [ -e "$WORKSPACE/.cursor-commands" ] || [ -L "$WORKSPACE/.cursor-commands" ]; then
    fail "SSOT self-alias present at $WORKSPACE/.cursor-commands (remove; SSOT must not link to itself)"
  else
    pass "SSOT workspace — .cursor-commands self-alias absent"
  fi
elif [ "$WS_KIND" = "ssot_checkout" ]; then
  pass "ssot_checkout — consumer .cursor-commands / .cursor/plans / .cursor/governance not required"
  if [ -L "$WORKSPACE/.cursor-commands" ] || [ -e "$WORKSPACE/.cursor-commands" ]; then
    rt=$(python3 -c "import os; print(os.path.realpath('$WORKSPACE/.cursor-commands'))")
    re="$GC_REAL"
    if [ "$rt" = "$re" ]; then
      pass ".cursor-commands -> $re (optional)"
    else
      fail ".cursor-commands points to $rt (expected $re / SSOT)"
    fi
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
if [ "$WS_KIND" = "ssot_checkout" ] || [ "$WS_KIND" = "ssot" ]; then
  pass "ssot-family — .cursor/plans not required"
elif [ ! -L "$WORKSPACE/.cursor/plans" ]; then
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

if [ "$WS_KIND" = "ssot_checkout" ] || [ "$WS_KIND" = "ssot" ]; then
  pass "ssot-family — .cursor/governance consumer layout not required"
elif [ -L "$WORKSPACE/.cursor/governance" ]; then
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
  elif [ "$WS_KIND" = "ssot_checkout" ]; then
    warn "SSOT checked out on '$ssot_branch', expected '$SSOT_BRANCH_EXPECTED' (ssot_checkout: not a gate)"
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
    warn "no cached origin/$SSOT_BRANCH_EXPECTED ref in SSOT clone — run git -C \"$GC\" fetch origin"
  elif [ "$ahead" -gt 0 ]; then
    if [ "$WS_KIND" = "ssot_checkout" ]; then
      warn "SSOT has $ahead unpushed commit(s) ahead of origin/$SSOT_BRANCH_EXPECTED (ssot_checkout: not a gate)"
    else
      fail "SSOT has $ahead unpushed commit(s) ahead of origin/$SSOT_BRANCH_EXPECTED — review before they linger (see git -C \"$GC\" log origin/$SSOT_BRANCH_EXPECTED..HEAD)"
    fi
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
  elif [ "$WS_KIND" = "ssot_checkout" ]; then
    warn "SSOT HEAD ${HEAD_SHA:0:7} != origin/$SSOT_BRANCH_EXPECTED ${ORIGIN_SHA:0:7} (ssot_checkout: not a gate)"
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

# Generated-artifact merge driver: git config is per-clone and untracked, so
# register idempotently every session (PR_OVERLAP_GUARDRAIL_V1). Attribute
# presence is expected on governance clones only — consumer repos legitimately
# have no merge=l9-generated entries.
echo ""
echo "=== git merge drivers (generated artifacts) ==="
if [ ! -x "$SCRIPT_DIR/ensure_git_merge_drivers.sh" ]; then
  warn "ensure_git_merge_drivers.sh missing — merge.l9-generated not registered (text-merge fallback)"
elif [ "$WS_KIND" = "ssot" ] || [ "$WS_KIND" = "ssot_checkout" ]; then
  if bash "$SCRIPT_DIR/ensure_git_merge_drivers.sh" "$WORKSPACE" --check-attributes >/dev/null 2>&1; then
    pass "merge.l9-generated driver registered ($WORKSPACE)"
  else
    warn "merge.l9-generated driver registration failed — generated merges fall back to text merge"
  fi
elif bash "$SCRIPT_DIR/ensure_git_merge_drivers.sh" "$WORKSPACE" >/dev/null 2>&1; then
  pass "merge.l9-generated driver registered ($WORKSPACE)"
else
  warn "merge.l9-generated driver registration failed — generated merges fall back to text merge"
fi
fi

if [ "$CHECK_MACHINE" -eq 1 ]; then
CURRENT_FAIL_CLASS=sessionend
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

CURRENT_FAIL_CLASS=graphiti
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
    warn "~/.cursor/graphiti.env missing (copy graphiti.env.example)"
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
  # The gate must NOT deny on a memory marker: repository-write authority comes
  # from worktree/branch isolation and the publication gate, never from a
  # phase-lock (rules/96-multi-agent-main-bound-execution, E7). This check used
  # to assert the opposite -- that graphiti_gate_lib.py contained
  # "gmp:phase_lock" -- so it must not be satisfied by the comment that now
  # explains the removal. Match executable code only.
  # Inspect the copy being changed. In a governance checkout the workspace IS
  # the source of truth for this file, and $GC points at the installed SSOT
  # clone -- which still carries the previous revision until this work merges.
  # Gating a pre-PR check on the installed clone would make every governance
  # change unable to publish the fix it contains. Consumer repos have no local
  # copy and fall back to $GC as before.
  GATE_LIB="$WORKSPACE/ops/graphiti/graphiti_gate_lib.py"
  [ -f "$GATE_LIB" ] || GATE_LIB="$GC/ops/graphiti/graphiti_gate_lib.py"
  if [ ! -f "$GATE_LIB" ]; then
    fail "graphiti_gate_lib.py missing"
  elif grep -v '^[[:space:]]*#' "$GATE_LIB" | grep -q "gmp:phase_lock"; then
    fail "graphiti_gate_lib.py still gates writes on gmp:phase_lock (E7 violation)"
  else
    pass "graphiti gate is hydration-only (no phase-lock write gate)"
  fi
  # Same reasoning as GATE_LIB above: prefer the workspace copy of the self-test.
  E2E_FULL="$WORKSPACE/ops/graphiti/test_gate_e2e_full.sh"
  [ -f "$E2E_FULL" ] || E2E_FULL="$GC/ops/graphiti/test_gate_e2e_full.sh"
  if bash "$E2E_FULL" >/dev/null 2>&1; then
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
  warn "memory-bank/ still present — deprecated; remove after Graphiti migrate (do not scaffold)"
else
  pass "memory-bank/ absent (retired)"
fi

# IDE profile is a convenience layer, never a gate — warn only, never fail.
if [ ! -x "$GC/ops/scripts/install_ide_profile.sh" ]; then
  warn "install_ide_profile.sh missing — IDE profile not managed"
elif [ -f "$WORKSPACE/.vscode/.l9-ide-desired-hash" ]; then
  pass "IDE profile applied ($(python3 -c '
import json,sys
print(json.load(open(sys.argv[1])).get("class", "unknown"))' "$WORKSPACE/.vscode/.l9-ide-desired-hash" 2>/dev/null || echo unknown))"
else
  warn "IDE profile not yet applied — run: bash \"\$HOME/.cursor-governance/ops/scripts/install_ide_profile.sh\" \"$WORKSPACE\""
fi

fi

emit_result
if [ "$FAIL" -eq 0 ]; then
  exit 0
fi
exit 1
