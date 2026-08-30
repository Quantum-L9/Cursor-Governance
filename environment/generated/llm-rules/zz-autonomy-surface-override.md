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
   with **no mid-execution push** → finish program/contract →
   `l4_local.py authorize-release` → `make pr` (kernel hook first, then
   checkers once, then push + PR; remediates=1). Campaign/make-pr end
   state is green + merge-ready. `PR_REMEDIATE=0` is opt-out only.
   Invoking `/l9-pr-remediation` then remediates **and merges** all open
   PRs in the target repo (bottom-up). Do **not** merge from the campaign
   path alone.
2a. Campaign first publish is `make pr` (`l9 pr` / `make -C "$GOV" pr
   WS="$PWD"`). That is a PATH rule for opening a PR, not a remediator
   deny. `/l9-pr-remediation` publishes an already-open PR with
   `make precommit-repo` then `git push` (and other non-destructive git).
   The execution gate must not workflow-deny those git/gh forms. `make
   push` and the MCP `create_pull_request` / `push_files` tools stay
   denied at every phase. Force-push stays effect-denied. Do not use
   `L9_PUBLISH_PATH_OVERRIDE` as the remediator path. When campaign
   `make pr` fails, fix what it reported. A consumer needs no `pr`
   target; there is no raw-push fallback for first publish.
   Enforced by `ops/autonomy/local_execution_gate.py`.
3. Force-push / hard-reset / admin-merge / secrets remain forbidden.
3a. Commit verification is not skippable. `git commit --no-verify` / `-n`,
   `git push --no-verify`, `core.hooksPath` overrides, `SKIP=` / `HUSKY=0`
   on a commit, `pre-commit uninstall`, and `.git/hooks/**` edits are
   denied at PreToolUse by `ops/autonomy/verification_bypass_gate.py`
   (contract `l9-commit-verification-integrity`, declared in
   `ops/config/commit-verification-contract.json`). Repair what the hook
   reported; breakglass `L9_VERIFY_BYPASS_AUTHORIZED=<reason>` is human/ops
   only.
4. Campaign work uses `campaign/<campaign_id>` as `PR_BASE`. Do not open
   campaign PRs against `main`. Do not mix with other feature branches.
5. Cursor surface (`L9_GOVERNANCE_SURFACE` is `cursor` or unset) MUST scoped-commit locally
   after each authored chunk (pathspecs; rule 49).
   Unique dirty files you authored are a rule failure. Do not ask.
   After finished work: `authorize-release` then `PR_REMEDIATE=0 make pr` /
   `l9 pr`. Do not run `make precommit-repo` then `make pr`. Tree kernels
   skip on Cursor; adapters still fire them on `make pr`. L4 remote gate
   still blocks mid-execution push.
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
- CLI: `python3 ops/autonomy/l4_local.py {begin|authorize-release|status}`.
  Kernels: `python3 ops/autonomy/kernel_gate.py {record|precommit}`
  (tree latch on adapter `make pr`; Cursor skips it).
- Breakglass: `L9_LOCAL_PUSH_AUTHORIZED=<reason>` or `L9_L4_LOCAL_AUTONOMY=0`;
  isolation: `L9_GIT_REVERT_AUTHORIZED` / `L9_GIT_BROAD_ADD_AUTHORIZED` /
  `L9_GIT_SWITCH_AUTHORIZED` / `L9_GIT_RESET_AUTHORIZED` /
  `L9_WORKTREE_ISOLATION=0`.
- Post-push (all surfaces after L4 release): `PR_REMEDIATE=0 make pr` /
  `l9 pr` to a green merge-ready PR. Merge only after `/l9-pr-remediation`
  writes `ops/autonomy/authorize_merge.py --all-open` and each PR is green +
  mergeable. Force-push / admin-merge stay forbidden. Tree kernels skip
  on Cursor; Claude Code desktop and Mobile still apply them on `make pr`.
- Stacked PRs: when a PR is already open for the workstream, the next PR
  bases on the open PR's head (bottom-up merge order). Rebase and conflict
  resolution are forbidden; one feature branch per program.

## Scratch hold / sacred WIP (never-lose)

- Never park `WIP/**` under `/tmp` or `.l9/scratch-hold/` to clean `make pr`.
- Shell gate denies WIP→/tmp moves, `rm -rf WIP`, `/tmp/cg-*-hold*` creation.
- Non-WIP park/restore: `ops/scripts/scratch_hold.py` (vault `.l9/scratch-hold/`).
- `make pr` / sessionStart restore-all; open holds fail-closed via `status`.

<!-- generated-from: ops/autonomy/surface_profile.yaml; do-not-edit -->
