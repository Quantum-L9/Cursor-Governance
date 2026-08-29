#!/usr/bin/env bash
# CI-025 / IMP-08 — clean-pyc removes exactly the disposable, and nothing else.
#
# The point of these cases is the refusals. A cleanup path only earns its place
# beside `ops/autonomy/git_guardrails.py` if it cannot be turned into the very
# command the guardrail refuses: an `rm -rf` whose target came from a variable
# that expanded empty.
set -uo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/ops/scripts/clean_pyc.sh"
pass=0
fail=0

ok() { printf '  ok   %s\n' "$1"; pass=$((pass + 1)); }
no() { printf '  FAIL %s — %s\n' "$1" "${2:-}" >&2; fail=$((fail + 1)); }

check() { # name expected_rc actual_rc
  if [[ "$2" == "$3" ]]; then ok "$1"; else no "$1" "expected rc $2, got $3"; fi
}

work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT

mkdir -p "$work/pkg/__pycache__" "$work/.pytest_cache" "$work/deep/a/b/__pycache__"
mkdir -p "$work/keep" "$work/.git/objects" "$work/.git/__pycache__"
printf 'x\n' >"$work/pkg/mod.py"
printf 'x\n' >"$work/keep/important.txt"
printf 'x\n' >"$work/pkg/__pycache__/mod.pyc"

# -- refusals ----------------------------------------------------------------
out="$(bash "$SCRIPT" "" 2>&1)"; rc=$?
check "empty argument is refused, not defaulted" 2 "$rc"
[[ "$out" == *"resolved empty"* ]] && ok "empty refusal names the cause" \
  || no "empty refusal names the cause" "$out"

bash "$SCRIPT" / >/dev/null 2>&1; check "refuses /" 2 "$?"
bash "$SCRIPT" "$work/nope" >/dev/null 2>&1; check "refuses a missing root" 2 "$?"

# -- plan mode destroys nothing ----------------------------------------------
CLEAN_PYC_MODE=plan bash "$SCRIPT" "$work" >/dev/null 2>&1
check "plan mode exits clean" 0 "$?"
[[ -d "$work/pkg/__pycache__" ]] && ok "plan mode removed nothing" \
  || no "plan mode removed nothing" "cache dir gone after a plan run"

# -- apply removes exactly the disposable ------------------------------------
bash "$SCRIPT" "$work" >/dev/null 2>&1
check "apply exits clean" 0 "$?"

for gone in "$work/pkg/__pycache__" "$work/.pytest_cache" "$work/deep/a/b/__pycache__"; do
  [[ -d "$gone" ]] && no "removed $gone" "still present" || ok "removed ${gone#"$work"/}"
done
for kept in "$work/keep/important.txt" "$work/pkg/mod.py" "$work/deep/a/b" "$work/.git/objects"; do
  [[ -e "$kept" ]] && ok "kept ${kept#"$work"/}" || no "kept ${kept#"$work"/}" "was removed"
done
# .git is pruned from the search, so a cache dir inside the object store is
# never a candidate — no cleanup path may reach into a repository's history.
[[ -d "$work/.git/__pycache__" ]] && ok "did not descend into .git" \
  || no "did not descend into .git" ".git/__pycache__ was removed"

# -- idempotent --------------------------------------------------------------
bash "$SCRIPT" "$work" >/dev/null 2>&1
check "second run is a no-op" 0 "$?"

printf '\nclean_pyc: %d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]]
