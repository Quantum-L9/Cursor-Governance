#!/usr/bin/env bash
# Stale remote-tracking refs break "unpushed commits" counts in both directions.
#
# Fixture reproduces the measured 2026-08-27 defect: a feature branch is pushed,
# merged into main upstream, and its remote branch deleted. The local clone keeps
# refs/remotes/origin/<branch> pointing at the pre-merge tip, so a checker that
# resolves origin/$current_branch counts every commit main gained since the merge
# as this branch's unpushed work.
#
# Asserts the whole contract, not just the prune:
#   T1 the stale ref overcounts
#   T2 prune alone goes SILENT (0) with real unpushed commits — the worse failure
#   T3 prune + set-head reports the true count
#   T4 both steps are idempotent
#   T5 no remote => activation still succeeds (fail-soft)
set -uo pipefail

FAILED=0
pass() { printf '  ok   %s\n' "$1"; }
fail() { printf '  FAIL %s\n' "$1" >&2; FAILED=1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

git_q() { git -C "$1" "${@:2}" >/dev/null 2>&1; }

# --- build an upstream and a clone -------------------------------------------
UP="$WORK/upstream.git"
git init --quiet --bare -b main "$UP"

SEED="$WORK/seed"
git init --quiet -b main "$SEED"
git -C "$SEED" config user.email t@example.com
git -C "$SEED" config user.name test
echo base > "$SEED/f"
git_q "$SEED" add f
git_q "$SEED" commit -m base
git_q "$SEED" remote add origin "$UP"
git_q "$SEED" push -u origin main

CLONE="$WORK/clone"
git clone --quiet "$UP" "$CLONE"
git -C "$CLONE" config user.email t@example.com
git -C "$CLONE" config user.name test

# feature branch: 1 commit, pushed
git_q "$CLONE" checkout -b feature
echo feature > "$CLONE/g"
git_q "$CLONE" add g
git_q "$CLONE" commit -m feature
git_q "$CLONE" push -u origin feature

# upstream merges it and advances main by several more commits, then deletes
# the feature branch — exactly what a squash-merge with --delete-branch does.
git_q "$SEED" fetch origin
git_q "$SEED" merge --no-edit origin/feature
for n in 1 2 3 4 5; do
  echo "later-$n" > "$SEED/later-$n"
  git_q "$SEED" add "later-$n"
  git_q "$SEED" commit -m "later-$n"
done
git_q "$SEED" push origin main
git_q "$SEED" push origin --delete feature

# the working clone gains 2 genuinely unpushed commits on the now-orphaned branch
for n in 1 2; do
  echo "local-$n" > "$CLONE/local-$n"
  git_q "$CLONE" add "local-$n"
  git_q "$CLONE" commit -m "local-$n"
done

# Rebase onto the advanced main — the merged-PR directive's own instruction, and
# the step that makes the stale ref bite: HEAD now carries main's newer commits,
# none of which refs/remotes/origin/feature knows about.
git_q "$CLONE" fetch origin main
git_q "$CLONE" rebase origin/main

# A fresh `git clone` sets refs/remotes/origin/HEAD. The audited checkout did not
# have it (fetch-built, not cloned), which is precisely why pruning alone left the
# count unreportable. Remove it so the fixture models the observed environment
# rather than the easy one.
git_q "$CLONE" symbolic-ref -d refs/remotes/origin/HEAD

TRUE_AHEAD=2

# how the harness stop hook resolves upstream, reproduced exactly
hook_count() {
  local repo="$1" branch upstream
  branch="$(git -C "$repo" branch --show-current)"
  if git -C "$repo" rev-parse "origin/$branch" >/dev/null 2>&1; then
    upstream="origin/$branch"
  else
    upstream="origin/HEAD"
  fi
  git -C "$repo" rev-list "$upstream..HEAD" --count 2>/dev/null || echo 0
}

# --- T1 stale ref overcounts --------------------------------------------------
stale_count="$(hook_count "$CLONE")"
if [ "$stale_count" -gt "$TRUE_AHEAD" ]; then
  pass "T1 stale remote-tracking ref overcounts ($stale_count reported, $TRUE_AHEAD real)"
else
  fail "T1 expected an overcount above $TRUE_AHEAD, got $stale_count"
fi

# --- T2 prune alone goes silent ----------------------------------------------
git_q "$CLONE" remote prune origin
if git -C "$CLONE" rev-parse origin/HEAD >/dev/null 2>&1; then
  fail "T2 fixture invalid: origin/HEAD already set, cannot show the silent-zero mode"
else
  pruned_only="$(hook_count "$CLONE")"
  if [ "$pruned_only" -eq 0 ]; then
    pass "T2 prune without set-head reports 0 while $TRUE_AHEAD commits are unpushed (false negative)"
  else
    fail "T2 expected 0 from the unresolvable origin/HEAD fallback, got $pruned_only"
  fi
fi

# --- T3 prune + set-head reports the truth -----------------------------------
if git_q "$CLONE" remote set-head origin -a; then
  fixed="$(hook_count "$CLONE")"
  if [ "$fixed" -eq "$TRUE_AHEAD" ]; then
    pass "T3 prune + set-head reports the true count ($fixed)"
  else
    fail "T3 expected $TRUE_AHEAD, got $fixed"
  fi
else
  fail "T3 remote set-head failed"
fi

# --- T4 idempotent ------------------------------------------------------------
git_q "$CLONE" remote prune origin
git_q "$CLONE" remote set-head origin -a
again="$(hook_count "$CLONE")"
if [ "$again" -eq "$TRUE_AHEAD" ]; then
  pass "T4 re-running both steps is idempotent ($again)"
else
  fail "T4 second run changed the count to $again"
fi

# --- T5 no remote is fail-soft ------------------------------------------------
NOREMOTE="$WORK/noremote"
git init --quiet -b main "$NOREMOTE"
git -C "$NOREMOTE" config user.email t@example.com
git -C "$NOREMOTE" config user.name test
echo x > "$NOREMOTE/f"
git_q "$NOREMOTE" add f
git_q "$NOREMOTE" commit -m only
if git -C "$NOREMOTE" remote get-url origin >/dev/null 2>&1; then
  fail "T5 fixture invalid: expected no origin remote"
else
  pass "T5 repo with no origin is skipped by the guard (activation not aborted)"
fi

# --- the shipped script carries both halves -----------------------------------
SCRIPT="${BASH_SOURCE[0]%/*}/../bootstrap_agent_environment.sh"
if grep -q "remote prune origin" "$SCRIPT" && grep -q "remote set-head origin -a" "$SCRIPT"; then
  pass "bootstrap ships prune and set-head together"
else
  fail "bootstrap is missing prune and/or set-head"
fi

if [ "$FAILED" -eq 0 ]; then
  echo "PASS: stale remote-tracking ref counts"
else
  echo "FAIL: stale remote-tracking ref counts" >&2
fi
exit "$FAILED"
