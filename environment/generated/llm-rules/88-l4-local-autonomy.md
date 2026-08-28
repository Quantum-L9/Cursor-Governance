---
description: L4 local autonomy — stacked local commits, no mid-execution push, then PR template. Kernels fire before precommit, not as L4.
---

# L4 Local Autonomy (no mid-execution push)

SSOT: `ops/autonomy/surface_profile.yaml` → `l4_local_autonomy` (CANONICAL_LAW §6.2).
Default ON (`L9_L4_LOCAL_AUTONOMY=1`).

## MUST

1. Execute programs/contracts on a **stacked feature branch** with **local commits only**.
2. **Do not** `git push`, `gh pr create`, or `make pr` mid-execution. `make pr`
   and the MCP write tools are mechanically denied until release; `git` and `gh`
   are not blocked (CANONICAL_LAW §6.2.4), so mid-execution restraint on those
   is doctrine you keep, not a gate that stops you.
3. **Do not** stall for push-approval pacing during local execution.
4. When the program/contract is finished locally, authorize release.
   Tree kernels are **not** an L4 phase. They fire as the first step of
   `make precommit-repo` via `ops/autonomy/kernel_gate.py` so hooks and
   tests run once on the post-kernel tree.
5. Authorize release, then publish **only** via Makefile checkers:

```bash
python3 ops/autonomy/l4_local.py begin --contract-id "<id>"   # if not begun
python3 ops/autonomy/l4_local.py authorize-release
PR_REMEDIATE=0 make pr
```

If the kernel hook fails, apply `kernels/Recursive Alignment.md` then
`kernels/Validate & Repair.md`, commit, `kernel_gate.py record`, and
re-run the same `make pr`. Do not run precommit or pytest first.

`make pr` runs the **governance** Makefile's `pr` target regardless of the
workspace repo or its Makefile — reach it with `l9 pr` /
`make -C "$GOV" pr WS="$PWD"` from a consumer checkout with no local `pr`
target. A consumer needs no `pr`/`pr-check` target; there is no raw-push
fallback where one is absent.

6. Do **not** merge from the campaign / `make pr` path. Campaign end state
   is green + merge-ready. Merge only after the user invokes
   `/l9-pr-remediation` (see `rules/48-make-pr-remediation.mdc`).
7. Program Execution campaigns: land work on `campaign/<campaign_id>` and set
   `PR_BASE` to that branch. Do **not** open campaign PRs against `main`.
   Do **not** mix campaign commits onto unrelated feature branches.

## Enforcement

- Claude PreToolUse: `local_execution_gate_wrap.py` → `ops/autonomy/local_execution_gate.py`
- Cursor `beforeShellExecution`: `ops/hooks/l4-local-execution-gate-shell.sh`
- Shared-worktree isolation (same gate): see `rules/49-shared-worktree-isolation.mdc`
- `make pr` / `open_pr_after_gate.sh` fail-closed without release receipt

## MUST NOT

- Mid-execution remote mutation
- Skipping the kernel hook by running pytest / pre-commit before `kernel_gate.py`
- Inventing "wait for push approval" contracts that recreate pacing stalls
- Merging from the campaign / `make pr` path (merge is `/l9-pr-remediation`)
- Force-push, admin-merge, or hard-reset
- Opening campaign PRs against `main`

<!-- generated-from: rules/88-l4-local-autonomy.mdc; do-not-edit -->
