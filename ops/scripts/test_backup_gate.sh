#!/usr/bin/env bash
# Fixture selftest for backup_gate.sh.
#
# Builds throwaway git clones under $TMPDIR and asserts each gate independently:
# sessionEnd reason filtering, background-agent suppression, the debounce window,
# the quiet-period activity guard, and the force override. Touches nothing outside
# $TMPDIR — in particular never the real ~/.cursor-governance clone or its stamp.
#
# Usage: bash ops/scripts/test_backup_gate.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)"
GATE="$SCRIPT_DIR/backup_gate.sh"

FIXTURE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/l9-backup-gate-test.XXXXXX")"
trap 'rm -rf "$FIXTURE_ROOT"' EXIT

export GOVERNANCE_BACKUP_STAMP="$FIXTURE_ROOT/stamp"
unset GOVERNANCE_BACKUP_FORCE 2>/dev/null || true

PASS=0
FAIL=0

check() {
  local label="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  PASS  $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $label"
    echo "        expected: $expected"
    echo "        actual:   $actual"
    FAIL=$((FAIL + 1))
  fi
}

# verdict <clone> <payload> → "proceed" | "skip" | "rc:<n>"
verdict() {
  local clone="$1" payload="$2" rc
  printf '%s' "$payload" | bash "$GATE" "$clone" >/dev/null 2>&1
  rc=$?
  case "$rc" in
    0) echo proceed ;;
    10) echo skip ;;
    *) echo "rc:$rc" ;;
  esac
}

make_clone() {
  # make_clone <name> [dirty] → path to a git repo whose tree is old enough to pass
  # the quiet-period guard
  local dir="$FIXTURE_ROOT/$1"
  mkdir -p "$dir"
  git -C "$dir" init -q 2>/dev/null
  git -C "$dir" config user.email test@example.com
  git -C "$dir" config user.name "Fixture"
  echo baseline >"$dir/tracked.txt"
  git -C "$dir" add -A >/dev/null 2>&1
  git -C "$dir" commit -qm baseline >/dev/null 2>&1
  if [ "${2:-}" = "dirty" ]; then
    echo edited >>"$dir/tracked.txt"
    # Backdate so the activity guard is not the thing under test.
    touch -t 200001010000 "$dir/tracked.txt"
  fi
  echo "$dir"
}

CLEAN_CLONE="$(make_clone clean)"
DIRTY_CLONE="$(make_clone dirty dirty)"

echo "=== sessionEnd reason filtering ==="
check "reason=completed proceeds" "proceed" \
  "$(verdict "$DIRTY_CLONE" '{"reason":"completed","is_background_agent":false}')"
check "reason=window_close proceeds" "proceed" \
  "$(verdict "$DIRTY_CLONE" '{"reason":"window_close","is_background_agent":false}')"
check "reason=user_close proceeds" "proceed" \
  "$(verdict "$DIRTY_CLONE" '{"reason":"user_close","is_background_agent":false}')"
check "reason=aborted skips" "skip" \
  "$(verdict "$DIRTY_CLONE" '{"reason":"aborted","is_background_agent":false}')"
check "reason=error skips" "skip" \
  "$(verdict "$DIRTY_CLONE" '{"reason":"error","is_background_agent":false}')"

echo "=== background agents ==="
check "background agent skips" "skip" \
  "$(verdict "$DIRTY_CLONE" '{"reason":"completed","is_background_agent":true}')"

echo "=== malformed / absent payload (fail-open) ==="
check "empty payload proceeds" "proceed" "$(verdict "$DIRTY_CLONE" '')"
check "non-JSON payload proceeds" "proceed" "$(verdict "$DIRTY_CLONE" 'not json at all')"
check "JSON array payload proceeds" "proceed" "$(verdict "$DIRTY_CLONE" '[1,2,3]')"

echo "=== debounce ==="
date +%s >"$GOVERNANCE_BACKUP_STAMP"
check "fresh stamp skips" "skip" \
  "$(verdict "$DIRTY_CLONE" '{"reason":"completed"}')"
echo "$(( $(date +%s) - 1000 ))" >"$GOVERNANCE_BACKUP_STAMP"
check "stale stamp (1000s > 900s) proceeds" "proceed" \
  "$(verdict "$DIRTY_CLONE" '{"reason":"completed"}')"
echo "$(( $(date +%s) - 100 ))" >"$GOVERNANCE_BACKUP_STAMP"
check "custom MIN_INTERVAL=60 proceeds at 100s" "proceed" \
  "$(GOVERNANCE_BACKUP_MIN_INTERVAL=60 verdict "$DIRTY_CLONE" '{"reason":"completed"}')"
echo "garbage" >"$GOVERNANCE_BACKUP_STAMP"
check "corrupt stamp proceeds" "proceed" \
  "$(verdict "$DIRTY_CLONE" '{"reason":"completed"}')"
rm -f "$GOVERNANCE_BACKUP_STAMP"
check "absent stamp proceeds" "proceed" \
  "$(verdict "$DIRTY_CLONE" '{"reason":"completed"}')"

echo "=== activity guard ==="
ACTIVE_CLONE="$(make_clone active)"
echo "written just now" >>"$ACTIVE_CLONE/tracked.txt"
check "just-written tree skips" "skip" \
  "$(verdict "$ACTIVE_CLONE" '{"reason":"completed"}')"
check "QUIET_SECONDS=0 disables the guard" "proceed" \
  "$(GOVERNANCE_BACKUP_QUIET_SECONDS=0 verdict "$ACTIVE_CLONE" '{"reason":"completed"}')"
UNTRACKED_CLONE="$(make_clone untracked)"
echo "new file" >"$UNTRACKED_CLONE/brand-new.txt"
check "untracked write counts as activity" "skip" \
  "$(verdict "$UNTRACKED_CLONE" '{"reason":"completed"}')"
check "clean tree proceeds (nothing to age out)" "proceed" \
  "$(verdict "$CLEAN_CLONE" '{"reason":"completed"}')"
check "non-git dir proceeds (defer to backup script)" "proceed" \
  "$(verdict "$FIXTURE_ROOT" '{"reason":"completed"}')"

echo "=== force override ==="
date +%s >"$GOVERNANCE_BACKUP_STAMP"
check "force beats debounce" "proceed" \
  "$(GOVERNANCE_BACKUP_FORCE=1 verdict "$DIRTY_CLONE" '{"reason":"completed"}')"
check "force beats reason filter" "proceed" \
  "$(GOVERNANCE_BACKUP_FORCE=1 verdict "$DIRTY_CLONE" '{"reason":"aborted"}')"
check "force beats activity guard" "proceed" \
  "$(GOVERNANCE_BACKUP_FORCE=1 verdict "$ACTIVE_CLONE" '{"reason":"completed"}')"
rm -f "$GOVERNANCE_BACKUP_STAMP"

echo ""
echo "PASS: $PASS   FAIL: $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
