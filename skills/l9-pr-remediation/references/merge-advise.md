<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: merge_advise
tags: [pr, merge, diagnose, git, stack-safe]
owner: igor_beylin
status: active
version: 2.1.0
updated: 2026-08-18
/L9_META -->

# Merge (Diagnose advise vs Converge action)

**CRITICAL:** Adoption = merge via git. NEVER manually write PR files from a diff.

```text
MERGE THE PR = ADOPT THE FILES
Git handles file transfer. NEVER unpack / copy / rewrite files from `gh pr diff`.
```

Violation: Manual file write from PR diff = CRITICAL — revert and re-merge via git.

## When

- **Diagnose (`/pr`):** advise only. **Never merge.** If the user wants merge, tell them to invoke `/l9-pr-remediation` (Converge). Do not run `gh pr merge` from Diagnose even after a verbal “looks good.”
- **Converge (`/l9-pr-remediation`):** merge is authorized only after
  FIRST_MERGE_GATE (full open-PR inventory, overlap matrix, stack probe,
  remediations published). Then MERGE_TRAIN **oldest `createdAt` first
  (bottom-up)**. Do not merge the first green PR. Zero unresolved
  `reviewThreads` (any author, paginated) immediately before each merge.

Write the receipt before the first `gh pr merge`:

```bash
GOV_PY="${GOV_PY:-$PWD/.venv/bin/python}"
"$GOV_PY" ops/autonomy/authorize_merge.py --repo {owner}/{repo} --all-open \
  --reason "l9-pr-remediation invoked"
```

## Preferred — GitHub merge (stack-safe)

Probe first: is this PR’s `headRefName` the `baseRefName` of another open PR?

```bash
# unstacked head — squash is safe
gh pr merge {number} --squash --delete-branch -b "{summary}"

# stacked parent — squash/rebase denied (silent delete-wins on the child).
# Merge children first, retarget them, or preserve ancestry:
gh pr merge {number} --merge --delete-branch -b "{summary}"
```

`ops/autonomy/merge_gate.py` fail-closes squash/rebase when the head is a
stack parent (unless human `L9_STACK_CHECK_BYPASS` / `L9_MERGE_AUTHORIZED`).

After a **parent squash**, never `gh pr update-branch` and never merge `main`
into the child. Rebase the child onto the new base:

```bash
git fetch origin
git rebase --onto origin/main <old-parent-tip> <child-branch>
```

Then publish the child with `UV_PYTHON=<native> PR_REMEDIATE=0 make pr` if
the Makefile has a `pr` target. Never raw `git push`.

## Local merge when GitHub merge is infra-blocked

Do **not** check out `main` in the remediation worktree and `make pr` from
there — `make pr` refuses `main`/`master`.

```bash
# only when GitHub merge is blocked by infra AND the user asked to land locally
# stay on a feature branch; do not publish from main
```

If Makefile `pr` exists, publish is `PR_REMEDIATE=0 make pr`. Never raw `git push`.

## Forbidden

- `git apply` / hand-copy from `gh pr diff` to adopt the PR
- Force-push to main
- `--admin` / bypass rules
- Merge during Diagnose (including “after user confirm” from Diagnose)
- Merge a red or conflicted PR
- Merge before FIRST_MERGE_GATE
- Squash/rebase a head that is the base of another open PR
- `gh pr update-branch` after squash-merging a parent
- Raw `git push` when Makefile `pr` exists
- Publish from the default branch (`make pr` refuses `main`/`master`)
