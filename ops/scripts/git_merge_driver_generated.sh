#!/usr/bin/env bash
# Custom git merge driver for generated artifacts (merge=l9-generated).
# Invoked by git as: driver %O %A %B %P   (base, ours, theirs, pathname)
#
# Policy: KEEP OURS — generated files are derived from source-of-truth inputs,
# so correctness is restored by regeneration AFTER the merge
# (ops/scripts/sync_generated_artifacts.py --force). Leaving %A untouched makes
# git install our version as the merge result.
#
# This driver never edits content itself. It appends the merged path to
# .l9/pr/regen-required.txt so the regeneration obligation is machine-checkable:
# remediation and publish flows must not claim a clean merge while that marker
# lists paths. See rules/53-pr-overlap-guardrail.mdc.
set -euo pipefail

# %O %A %B %P — the first three are temp-file paths; %P is the pathname.
PATHNAME="${4:-}"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$repo_root" ]; then
  echo "ERROR: merge driver could not resolve repo top-level" >&2
  exit 1
fi

marker_dir="$repo_root/.l9/pr"
mkdir -p "$marker_dir" 2>/dev/null || true
if [ -n "$PATHNAME" ]; then
  printf '%s\n' "$PATHNAME" >> "$marker_dir/regen-required.txt"
fi

# Success with %A (ours) unchanged == keep ours.
exit 0
