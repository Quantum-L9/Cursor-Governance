#!/usr/bin/env bash
# Retire the live runtime and rewind the target to the campaign's pre-bind base
# so the task stack is rebuilt from a seal that has just been corrected.
set -euo pipefail

ISO="$HOME/.l9/gov-worktrees/pe-kernel-bind"
TARGET="$HOME/.l9/program-worktrees/pe-kernel-bind"
BASE="${1:-6189bf1}"
STAMP="$(date +%Y%m%d-%H%M%S)"

if [ -d "$HOME/.l9/programs/pe-kernel-bind" ]; then
  mv "$HOME/.l9/programs/pe-kernel-bind" "$HOME/.l9/programs/stale/pe-kernel-bind-retired-$STAMP"
fi

git -C "$TARGET" worktree prune
for branch in $(git -C "$TARGET" branch --format='%(refname:short)' | grep '^pec/' || true); do
  git -C "$TARGET" branch -m "$branch" "retired/${branch//\//-}-$STAMP"
done

git -C "$TARGET" checkout -q -B campaign-base/pe-kernel-bind "$BASE"
git -C "$TARGET" branch -f campaign/pe-kernel-bind "$BASE"
git -C "$TARGET" fetch -q -f "$ISO" feat/pe-kernel-bind:feat/pe-kernel-bind

cd "$ISO"
L9_CAMPAIGN_UNTIL_DEBUG=1 make campaign \
  INTENT="$HOME/.cursor/plans/pe-kernel-bind.activate.yaml" \
  CAMPAIGN_UNTIL=arm 2>&1 | grep -E "admit|arm TASK|FAIL" | tail -3
