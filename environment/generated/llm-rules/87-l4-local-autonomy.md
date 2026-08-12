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
5. Authorize release, then push scoped PRs using `PULL_REQUEST_TEMPLATE.md`:

```bash
python3 ops/autonomy/l4_local.py begin --contract-id "<id>"   # if not begun
python3 ops/autonomy/l4_local.py record-kernels
python3 ops/autonomy/l4_local.py authorize-release
make pr
```

6. After push: run `l9-pr-remediation` Converge — turn CI green, resolve all
   code-review agent comments, reach mergeable.
7. Launching a program or clicking Build on a plan **is** merge authorization
   for that stack — do not wait for a separate merge ask. After remediation
   reaches mergeable: merge. If older open PRs exist (earlier `createdAt` than
   the PR just pushed), remediate and merge those **bottom-up first** so older
   work is not rebased onto a newer main.

## Enforcement

- Claude PreToolUse: `local_execution_gate_wrap.py` → `ops/autonomy/local_execution_gate.py`
- Cursor `beforeShellExecution`: `ops/hooks/l4-local-execution-gate-shell.sh`
- Shared-worktree isolation (same gate): see `rules/88-shared-worktree-isolation.mdc`
- `make pr` / `open_pr_after_gate.sh` fail-closed without release receipt

## MUST NOT

- Mid-execution remote mutation
- Skipping post-exec kernels before first push/PR
- Inventing "wait for push approval" contracts that recreate pacing stalls
- Merging newer tips before older open PRs when bottom-up order is required

<!-- generated-from: rules/87-l4-local-autonomy.mdc; do-not-edit -->
