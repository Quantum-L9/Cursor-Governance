---
description: Autonomy Velocity Override — adapter surfaces outrank ask-first commit rules
---

# Autonomy Velocity Override (adapter surfaces) + L4 local autonomy

When `L9_GOVERNANCE_SURFACE` is `claude-code`, `codex`, `gemini`, or `manus`
AND `L9_AUTONOMY_ENABLED=true`:

1. This override **outranks** `99-no-auto-commit` (git mutation gate; push-approval twin retired)
   for scoped feature-branch **local commits**. Remote push/PR remain gated
   by L4 local autonomy (below), not by per-action chat pacing.
2. Completing reversible work MUST proceed L4-local: stacked-branch commits
   with **no mid-execution push** → finish program/contract → run
   `kernels/Recursive Alignment.md` + `kernels/Validate & Repair.md` →
   `l4_local.py authorize-release` → push → PR (`PULL_REQUEST_TEMPLATE.md`)
   → `l9-pr-remediation` Converge (green + resolve review threads) without
   mid-task push asks. Program/plan Build launch authorizes merge for that
   stack (no separate merge ask).
3. Force-push / hard-reset / admin-merge / secrets remain forbidden.
4. Older open PRs: remediate + merge **bottom-up** by `createdAt` before newer
   tips, so older work is not rebased onto a freshly updated main.
5. Cursor surface stays ask-first for commits except campaign packet /
   `make pr` remediation; L4 remote gate still blocks mid-execution push.
6. Source of truth: `ops/autonomy/surface_profile.yaml` — do not fork this text.

## L4 Local Autonomy (all surfaces; default ON)

- `L9_L4_LOCAL_AUTONOMY=1` (default): deny `git push`, `gh pr create`, and
  `make pr` until `.l9/autonomy/l4-release-receipt.json` authorizes release.
- Shared-worktree isolation (default ON): deny `git revert`, `git reset`,
  branch `checkout`/`switch`, broad `git add -A/--all/./-u`, and
  `git diff --name-only | … git add` scoop loops that destroy parallel
  agents' dirty files (2026-08-12 plan.md + branch-thrash incident).
- Enforcement: `ops/autonomy/local_execution_gate.py` +
  `worktree_isolation_gate.py` (Claude PreToolUse + Cursor beforeShellExecution).
- CLI: `python3 ops/autonomy/l4_local.py {begin|record-kernels|authorize-release|status}`.
- Breakglass: `L9_LOCAL_PUSH_AUTHORIZED=<reason>` or `L9_L4_LOCAL_AUTONOMY=0`;
  isolation: `L9_GIT_REVERT_AUTHORIZED` / `L9_GIT_BROAD_ADD_AUTHORIZED` /
  `L9_GIT_SWITCH_AUTHORIZED` / `L9_GIT_RESET_AUTHORIZED` /
  `L9_WORKTREE_ISOLATION=0`.
- Post-push: `l9-pr-remediation` → green → resolve reviews → merge (program/
  plan Build launch is the auth); older open PRs bottom-up first.

## Scratch hold / sacred WIP (never-lose)

- Never park `WIP/**` under `/tmp` or `.l9/scratch-hold/` to clean `make pr`.
- Shell gate denies WIP→/tmp moves, `rm -rf WIP`, `/tmp/cg-*-hold*` creation.
- Non-WIP park/restore: `ops/scripts/scratch_hold.py` (vault `.l9/scratch-hold/`).
- `make pr` / sessionStart restore-all; open holds fail-closed via `status`.

<!-- generated-from: ops/autonomy/surface_profile.yaml; do-not-edit -->
