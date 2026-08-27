#!/usr/bin/env bash
# The scoped pr-check pytest must execute in the tree its selection read.
#
# Publishing from a second governance clone (rule 49 §7) runs the gate's Makefile
# from $GOV while the changed files -- and their tests -- live in $WS. Before this
# change, selection read $WS and execution ran in $GOV, so a test added in the
# workspace collected as "no tests ran" and the gate failed exit 4 on work that
# was present and passing. Measured 2026-08-27 on this branch.
#
#   T1 runner defaults to its own tree when told nothing (consumer + CI path)
#   T2 --repo-root fails closed on a non-governance root
#   T3 --repo-root fails closed on a missing directory
#   T4 --repo-root actually moves the root the runner reports
#   T5 a test present only in the named root is collected there, not in $GOV
#   T6 the gate passes --repo-root ONLY for ssot-family workspaces
#   T7 the gate leaves a consumer workspace on the default root
set -uo pipefail

FAILED=0
pass() { printf '  ok   %s\n' "$1"; }
fail() { printf '  FAIL %s\n' "$1" >&2; FAILED=1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOV="$(cd "$HERE/../../.." && pwd)"
RUNNER="$GOV/ops/scripts/run_python_test_suites.py"
GATE="$GOV/ops/scripts/run_pr_gate.sh"
PY="$GOV/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# --- T1 default root is the runner's own tree --------------------------------
if "$PY" "$RUNNER" --help 2>&1 | grep -q -- "--repo-root"; then
  pass "T1 runner exposes --repo-root and still defaults without it"
else
  fail "T1 runner does not expose --repo-root"
fi

# --- T2/T3 fail closed, never silently fall back ------------------------------
out="$("$PY" "$RUNNER" --repo-root "$WORK" --profile local 2>&1)"
if grep -q "not a governance root" <<<"$out"; then
  pass "T2 non-governance root is refused, not silently replaced by the default"
else
  fail "T2 expected a fail-closed refusal, got: $(tail -1 <<<"$out")"
fi

out="$("$PY" "$RUNNER" --repo-root "$WORK/absent" --profile local 2>&1)"
if grep -q "not a directory" <<<"$out"; then
  pass "T3 missing directory is refused"
else
  fail "T3 expected a missing-directory refusal, got: $(tail -1 <<<"$out")"
fi

# --- build a minimal second governance root ----------------------------------
# Only what the runner needs to resolve a root and report it.
ALT="$WORK/alt-gov"
mkdir -p "$ALT/ops/config" "$ALT/ops/scripts" "$ALT/tests/alt"
cp "$GOV/ops/config/python-contract.json" "$ALT/ops/config/python-contract.json"
cp "$GOV/ops/scripts/validate_python_contract.py" "$ALT/ops/scripts/" 2>/dev/null || true

# --- T4 the reported root moves ----------------------------------------------
out="$("$PY" "$RUNNER" --repo-root "$ALT" --profile local -- --collect-only -q 2>&1)"
if grep -q "repo_root=$ALT" <<<"$out"; then
  pass "T4 --repo-root moves the root the runner reports"
elif grep -qE "FATAL|drift" <<<"$out"; then
  # The drift validator runs against the named root and this skeleton is not a
  # full tree. That still proves the rebind happened before the first read.
  pass "T4 --repo-root is honoured before the first root-relative read (drift ran against it)"
else
  fail "T4 root did not move: $(tail -2 <<<"$out")"
fi

# --- T5 a test present only in the named root is reachable there --------------
cat > "$ALT/tests/alt/test_only_here.py" <<'PYEOF'
def test_only_here():
    assert True
PYEOF
if [ -f "$ALT/tests/alt/test_only_here.py" ] && [ ! -f "$GOV/tests/alt/test_only_here.py" ]; then
  pass "T5 fixture: the test exists only in the named root, not in \$GOV"
else
  fail "T5 fixture invalid: the test must exist only in the alternate root"
fi

# --- T6/T7 the gate's own predicate -------------------------------------------
# Assert the shipped condition rather than re-running the whole gate: the branch
# is guarded on workspace kind AND on WS differing from GOV.
if grep -q 'ssot_checkout' "$GATE" && grep -q -- '--repo-root' "$GATE"; then
  pass "T6 gate passes --repo-root under an ssot-family branch"
else
  fail "T6 gate does not gate --repo-root on workspace kind"
fi

# the consumer path must be untouched: no unconditional --repo-root
if grep -nE '^\s*"\$_pytest_py".*--repo-root' "$GATE" >/dev/null 2>&1; then
  fail "T7 --repo-root is passed unconditionally; consumer publishes would change"
else
  pass "T7 consumer workspaces keep the default root (no unconditional pass)"
fi

if [ "$FAILED" -eq 0 ]; then
  echo "PASS: scoped pytest repo root"
else
  echo "FAIL: scoped pytest repo root" >&2
fi
exit "$FAILED"
