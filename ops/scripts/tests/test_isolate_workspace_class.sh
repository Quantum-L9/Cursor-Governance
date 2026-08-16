#!/usr/bin/env bash
# Isolate workspace class: predicate, honest banners, nested --machine only,
# paired skip, toolchain bind. Does not mutate ~/.cursor-governance.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=../resolve_governance_paths.sh
source "$OPS_DIR/resolve_governance_paths.sh"

PASS=0
pass() {
  PASS=$((PASS + 1))
  echo "PASS T$PASS: $1"
}

fail_now() {
  echo "FAIL: $1" >&2
  exit 1
}

TMP="$(mktemp -d "${TMPDIR:-/tmp}/l9-isolate-class.XXXXXX")"
ISO="$HOME/.l9/gov-worktrees/_isolate-class-test-$$"
PROG="$HOME/.l9/programs/_isolate-class-test-$$/worktrees/TASK-001"
trap 'rm -rf "$TMP" "$ISO" "$HOME/.l9/programs/_isolate-class-test-$$"' EXIT

mkdir -p "$ISO" "$PROG" "$TMP/consumer/skills" "$TMP/consumer/rules"
printf 'x\n' >"$TMP/consumer/skills/AUTONOMY_MANIFEST.yaml"
printf 'x\n' >"$TMP/consumer/rules/RULES-MANIFEST.yaml"

is_l9_isolate_workspace "$ISO" || fail_now "gov-worktrees isolate should match"
is_l9_isolate_workspace "$PROG" || fail_now "programs worktree isolate should match"
if is_l9_isolate_workspace "$TMP/consumer"; then
  fail_now "temp consumer must not match isolate"
fi
if is_l9_isolate_workspace "$HOME/.cursor-governance"; then
  fail_now "SSOT clone must not match isolate"
fi
pass "isolate predicate true/false"

(
  unset CI GITHUB_ACTIONS L9_GOVERNANCE_SURFACE
  should_skip_consumer_symlink_checks "$ISO" || fail_now "isolate must skip consumer checks"
  if should_skip_consumer_symlink_checks "$TMP/consumer"; then
    fail_now "consumer clone must not skip consumer checks"
  fi
  CI=1 should_skip_consumer_symlink_checks "$TMP/consumer" || fail_now "CI must skip"
)
pass "paired skip predicate"

if grep -q 'sessionEnd hook (full gate: check_governance_wiring.sh)' \
  "$OPS_DIR/validate_governance_symlinks.sh"; then
  fail_now "nested full-gate sessionEnd wrap still present"
fi
grep -q 'check_governance_wiring.sh" --machine' "$OPS_DIR/validate_governance_symlinks.sh" \
  || fail_now "validate_governance_symlinks must call --machine only"
if grep -E 'check_governance_wiring.sh" "\$WORKSPACE"' "$OPS_DIR/validate_governance_symlinks.sh"; then
  fail_now "validate_governance_symlinks must not re-run full workspace gate"
fi
pass "nested double-run retired"

out="$(bash "$OPS_DIR/check_governance_wiring.sh" --workspace "$TMP/consumer" 2>&1 || true)"
echo "$out" | grep -q 'RESULT: FAIL — consumer workspace wiring' \
  || fail_now "missing consumer banner: $out"
if echo "$out" | grep -q 'sessionEnd hook incomplete'; then
  fail_now "consumer symlink fail relabeled as sessionEnd: $out"
fi
pass "consumer missing symlink is not sessionEnd"

out="$(bash "$OPS_DIR/check_governance_wiring.sh" "$ISO" 2>&1 || true)"
echo "$out" | grep -q 'skip consumer workspace wiring (isolate under \$HOME/.l9)' \
  || fail_now "isolate must skip consumer section: $out"
if echo "$out" | grep -q 'RESULT: FAIL — consumer workspace wiring'; then
  fail_now "isolate must not fail consumer wiring: $out"
fi
if echo "$out" | grep -q '.cursor-commands missing' && echo "$out" | grep -q 'sessionEnd hook incomplete'; then
  fail_now "isolate missing symlink blamed on sessionEnd: $out"
fi
pass "isolate skip + honest machine RESULT"

git -C "$ISO" init >/dev/null 2>&1
tool="$(resolve_gov_toolchain_root "$ISO" "$HOME/.cursor-governance")"
[ -n "$tool" ] || fail_now "toolchain root empty"
if [ "$tool" = "$ISO" ]; then
  fail_now "isolate must not be its own toolchain root"
fi
[ -x "$tool/.venv/bin/python" ] || [ -x "$tool/.venv/bin/python3" ] \
  || fail_now "toolchain root has no locked interpreter: $tool"
pass "toolchain root is donor or primary, not isolate"

echo "RESULT: PASS — isolate workspace class ($PASS checks)"
