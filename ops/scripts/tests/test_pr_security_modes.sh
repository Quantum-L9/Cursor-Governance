#!/usr/bin/env bash
# Security gate modes: a missing scanner binary is a FAILURE on the publish path
# and a SKIP in local dev (INV-5).
#
# Covers audit finding B-11 and acceptance tests T-11, T-12.
#
# The runtime this was written against had no gitleaks binary at all, and
# run_pr_security.sh's policy of skipping an absent checker meant the secret
# scan silently did not run while the summary still read PASS. Both cases below
# therefore run with a PATH stripped of every scanner — the broken fixture is
# the point.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SECURITY="$SCRIPTS_DIR/run_pr_security.sh"
PR_GATE="$SCRIPTS_DIR/run_pr_gate.sh"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/l9-pr-security.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0
pass() { PASS=$((PASS + 1)); echo "PASS T$PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }

# A workspace with exactly one changed Python file, so the scanners have
# something to be absent *for*.
ws="$TMP_ROOT/ws"
mkdir -p "$ws"
git init -q "$ws"
git -C "$ws" config user.email l9@example.com
git -C "$ws" config user.name L9
printf 'print("base")\n' > "$ws/base.py"
git -C "$ws" add base.py
git -C "$ws" commit -qm "base"
printf 'print("changed")\n' > "$ws/changed.py"
git -C "$ws" add changed.py

# A PATH with git and the shell but no gitleaks, uv, uvx or semgrep.
BARE_PATH="/usr/bin:/bin"

run_mode() { # $1=mode -> writes output to stdout, returns exit code
  set +e
  env -i HOME="$TMP_ROOT" PATH="$BARE_PATH" \
    bash "$SECURITY" --mode "$1" "$ws" 2>&1
  local rc=$?
  set -e
  return $rc
}

# T1 — gate mode: an absent scanner is a failure that names the tool.
set +e
gate_out="$(run_mode gate)"
gate_rc=$?
set -e
[ "$gate_rc" -ne 0 ] || fail "gate mode exited 0 with every scanner absent"
grep -q "gitleaks is NOT INSTALLED" <<<"$gate_out" \
  || fail "gate mode did not name gitleaks as missing"
grep -q "provision:" <<<"$gate_out" \
  || fail "gate mode did not print a provisioning command"
grep -q "RESULT: FAIL" <<<"$gate_out" || fail "gate mode did not report FAIL"
pass "gate mode fails and names the absent scanner"

# T2 — advisory mode: the same environment passes, with the skip visible.
set +e
adv_out="$(run_mode advisory)"
adv_rc=$?
set -e
[ "$adv_rc" -eq 0 ] || fail "advisory mode should not block local dev (rc=$adv_rc)"
grep -q "SKIP: gitleaks not available" <<<"$adv_out" \
  || fail "advisory mode did not record the skip"
grep -q "RESULT: PASS" <<<"$adv_out" || fail "advisory mode did not report PASS"
pass "advisory mode skips with a warning and does not block"

# T3 — the mode is stated in the summary, so a reader can tell which ran.
grep -q "mode=gate" <<<"$gate_out" || fail "gate summary omits its mode"
grep -q "mode=advisory" <<<"$adv_out" || fail "advisory summary omits its mode"
pass "summary states the mode that produced it"

# T4 — an unknown mode is rejected rather than silently treated as advisory.
set +e
env -i HOME="$TMP_ROOT" PATH="$BARE_PATH" bash "$SECURITY" --mode loose "$ws" >/dev/null 2>&1
bad_rc=$?
set -e
[ "$bad_rc" -eq 2 ] || fail "unknown mode should exit 2, got $bad_rc"
pass "unknown mode is rejected"

# T5 — the publish path opts in to gate mode.
grep -Eq 'run_pr_security\.sh"? --mode gate' "$PR_GATE" \
  || fail "run_pr_gate.sh must invoke the security gate in gate mode"
pass "publish path invokes gate mode"



# T6 — a semgrep exit that means "rules never loaded" is not reported as findings.
# semgrep exits 1 for FINDINGS and >1 when it cannot resolve its config. Reporting
# every non-zero exit as "found issues in changed files" sent the reader hunting a
# defect that was not in the diff — the real cause was a blocked registry fetch.
grep -q 'semgrep registry rules unreachable (blocker: allowlist)' "$SECURITY" \
  || fail "security gate cannot distinguish unreachable rules from findings"
grep -q 'rc" -eq 1' "$SECURITY" \
  || fail "security gate does not treat exit 1 as the findings case"
pass "semgrep separates 'rules unreachable' from 'issues found'"

# T7 — that distinction must not become a pass. Missing telemetry fails closed
# (rules/53 E6); only the MESSAGE changed, never the verdict.
grep -q 'fail "semgrep registry rules unreachable' "$SECURITY" \
  || fail "unreachable rules must still FAIL, not warn or pass"
pass "unreachable rules still fail closed"
echo "OK: $PASS assertions"
