#!/usr/bin/env bash
# Regression suite for ops/scripts/lib/repo_write_lock.sh.
# Writes only under $TMPDIR (matching test_install_ide_profile.sh).
# Run: make repo-write-lock-test

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB="$SCRIPT_DIR/lib/repo_write_lock.sh"

FAILED=0
pass() { echo "  PASS: $1"; }
fail() {
  echo "  FAIL: $1"
  FAILED=1
}
check() {
  if [ "$2" = "$3" ]; then pass "$1"; else fail "$1 (expected '$3', got '$2')"; fi
}

# Isolate HOME so the lock never collides with a real session's lock.
FAKE_HOME="$(mktemp -d)"
WS_A="$(mktemp -d)"
WS_B="$(mktemp -d)"
trap 'rm -rf "$FAKE_HOME" "$WS_A" "$WS_B"' EXIT
export HOME="$FAKE_HOME"
mkdir -p "$HOME/.cursor"

# shellcheck source=lib/repo_write_lock.sh
. "$LIB"

echo "=== repo_write_lock ==="

repo_write_lock_acquire "$WS_A" 0
check "acquire on a free workspace" "$?" "0"

holder="$(repo_write_lock_holder "$WS_A")"
case "$holder" in
  "$$ "*) pass "ledger records the holder pid" ;;
  *) fail "ledger records the holder pid (got '$holder')" ;;
esac

repo_write_lock_held_by_me "$WS_A"
check "re-entrant for the owning process tree" "$?" "0"

out="$(env -u L9_REPO_WRITE_LOCK_OWNER bash -c ". '$LIB'; repo_write_lock_acquire '$WS_A' 0; echo \$?")"
check "second process is refused" "$out" "1"

out="$(env -u L9_REPO_WRITE_LOCK_OWNER bash -c ". '$LIB'; repo_write_lock_acquire '$WS_B' 0; echo \$?")"
check "a different workspace is unaffected" "$out" "0"
rm -rf "$(repo_write_lock_dir "$WS_B")"

note="$(repo_write_lock_skip_note "$WS_A")"
case "$note" in
  "repo-write lock held by "*) pass "skip note names the holder" ;;
  *) fail "skip note names the holder (got '$note')" ;;
esac

repo_write_lock_release
check "release removes the lock" "$(repo_write_lock_holder "$WS_A")" ""

# A ledger owned by a dead pid must not wedge the workspace forever.
dead_dir="$(repo_write_lock_dir "$WS_A")"
mkdir -p "$dead_dir"
printf '999999 %s %s stale-test\n' "$(date +%s)" "$WS_A" >"$dead_dir/owner"
out="$(env -u L9_REPO_WRITE_LOCK_OWNER bash -c ". '$LIB'; repo_write_lock_acquire '$WS_A' 0; echo \$?")"
check "dead holder is broken through" "$out" "0"
rm -rf "$dead_dir"

# An ancient ledger from a live-but-forgotten pid must expire.
mkdir -p "$dead_dir"
printf '%s 1 %s ancient-test\n' "$$" "$WS_A" >"$dead_dir/owner"
out="$(env -u L9_REPO_WRITE_LOCK_OWNER bash -c ". '$LIB'; repo_write_lock_acquire '$WS_A' 0; echo \$?")"
check "stale ledger is broken through" "$out" "0"
rm -rf "$dead_dir"

out="$(env -u L9_REPO_WRITE_LOCK_OWNER L9_REPO_WRITE_LOCK=0 bash -c ". '$LIB'; repo_write_lock_acquire '$WS_A' 0; echo \$?")"
check "L9_REPO_WRITE_LOCK=0 disables the lock" "$out" "0"

if [ "$FAILED" -eq 0 ]; then
  echo "RESULT: PASS"
else
  echo "RESULT: FAIL"
fi
exit "$FAILED"
