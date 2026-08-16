---
description: L4 local autonomy — stacked local commits, no mid-execution push, kernels then PR template.
---

# L4 Local Autonomy (no mid-execution push)

SSOT: `ops/autonomy/surface_profile.yaml` → `l4_local_autonomy` (CANONICAL_LAW §6.2).
Default ON (`L9_L4_LOCAL_AUTONOMY=1`).

## MUST

1. Execute programs/contracts on a **stacked feature branch** with **local commits only**.
2. **Do not** `git push`, `gh pr create`, or `make pr` mid-execution.
3. **Do not** stall for push-approval pacing during local execution.
4. When the program/contract is finished locally, run:
   - `kernels/Recursive Alignment.md`
   - then `kernels/Validate & Repair.md`
   on the finished tree.
5. Authorize release, then publish **only** via Makefile checkers:

```bash
python3 ops/autonomy/l4_local.py begin --contract-id "<id>"   # if not begun
python3 ops/autonomy/l4_local.py record-kernels
python3 ops/autonomy/l4_local.py authorize-release
make pr
```

6. `PR_AUTOMERGE=1` may merge only this exact green mergeable PR head.
   `PR_AUTOMERGE=0` remains the opt-out. `/l9-pr-remediation` still authorizes
   ordinary merge of all open PRs (see `rules/48-make-pr-remediation.mdc`).
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
- Skipping post-exec kernels before first push/PR
- Inventing "wait for push approval" contracts that recreate pacing stalls
- Unbounded merge, force-push, admin-merge, or hard-reset
- Force-push, admin-merge, or hard-reset
- Opening campaign PRs against `main`

<!-- generated-from: rules/88-l4-local-autonomy.mdc; do-not-edit -->
