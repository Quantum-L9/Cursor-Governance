---
description: L4 local autonomy - stacked local commits, exact-tree release authorization, then the single make pr publication ceremony.
---

# L4 Local Autonomy (no mid-execution push)

SSOT: `ops/autonomy/surface_profile.yaml` → `l4_local_autonomy` (CANONICAL_LAW §6.2,
as amended by `PUBLISH_ASSURANCE_DECOUPLING_V1`).
Default ON (`L9_L4_LOCAL_AUTONOMY=1`).

L4 owns two things: the local-execution phase, and authorization of the exact
finished tree. It does not run validation and it does not own repair.

## MUST

1. Execute programs/contracts on a **stacked feature branch** with **local commits only**.
2. **Do not** `git push`, `gh pr create`, or `make pr` mid-execution. `make pr`
   and the MCP write tools are mechanically denied until release; `git` and `gh`
   are not blocked by L4 state (CANONICAL_LAW §6.2.4). A raw push of a branch
   with no open PR, or `gh pr create`, is denied by effect as a first
   publication (§6.2.8, `ops/autonomy/first_publication_gate.py`); a push
   advancing an open PR stays allowed. Mid-execution restraint on the latter is
   doctrine you keep, not a gate that stops you.
3. **Do not** stall for push-approval pacing during local execution.
4. When the program/contract is finished locally on **every** surface
   (Cursor, Claude Code desktop, Claude Code Mobile): scoped-commit, `begin`
   if not begun, `authorize-release`, then publish once through `make pr`.
   Do not run `make precommit-repo` then `make pr`.

```bash
python3 ops/autonomy/l4_local.py begin --contract-id "<id>"   # if not begun
python3 ops/autonomy/l4_local.py authorize-release
PR_REMEDIATE=0 make pr   # or l9 pr / make -C "$GOV" pr WS="$PWD"
```

5. Treat `make pr` as preparation then validation. Its existing deterministic
   preparation (formatters, generated-artifact heal) may write before
   validation; once validation begins it is observational and fail-closed.
   `make pr` never runs `kernels/Recursive Alignment.md` or
   `kernels/Validate & Repair.md`; those stay explicit capabilities you invoke
   on your own, outside the publication gate.
6. When validation fails, stop on that evidence. Repair is a separate action,
   never a hidden step of the validator. Any authored repair that changes tree
   content spends the release receipt (`ops/autonomy/receipt_binding.py`
   `tree_digest`): run `authorize-release` again before the next `make pr`, or
   the remote check refuses with `L4 receipt stale`.

On every surface, `make pr` runs the **governance** Makefile's
`pr` target regardless of the workspace repo or its Makefile — reach it
with `l9 pr` / `make -C "$GOV" pr WS="$PWD"` from a consumer checkout
with no local `pr` target. A consumer needs no additional local target;
there is no raw-push fallback where one is absent.

7. Do **not** merge from the `make pr` path. Its end state is green +
   merge-ready. Merge only after the user invokes `/l9-pr-remediation`
   (see `rules/48-make-pr-remediation.mdc`).

## Enforcement

- Claude PreToolUse: `local_execution_gate_wrap.py` → `ops/autonomy/local_execution_gate.py`
- Cursor `beforeShellExecution`: `ops/hooks/l4-local-execution-gate-shell.sh`
- Shared-worktree isolation (same gate): see `rules/49-shared-worktree-isolation.mdc`
- `make pr` / `open_pr_after_gate.sh` fail-closed without a release receipt that
  matches the worktree

## MUST NOT

- Mid-execution remote mutation
- Treating a validation failure as permission for the validator to repair the
  tree, or publishing a repaired tree on the pre-repair authorization
- Inventing "wait for push approval" contracts that recreate pacing stalls
- Merging from the `make pr` path (merge is `/l9-pr-remediation`)
- Force-push, admin-merge, or hard-reset

<!-- generated-from: rules/88-l4-local-autonomy.mdc; do-not-edit -->
