<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: merge_advise
tags: [pr, merge, diagnose, git, stack-safe]
owner: igor_beylin
status: active
version: 2.2.0
updated: 2026-10-12
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
- **Converge (`/l9-pr-remediation`):** remediates to merge readiness and
  stops at **MERGE_PENDING**. Invoking it is not merge authority
  (CANONICAL_LAW §6.2.12). A PR merges only when FIRST_MERGE_GATE holds
  (full open-PR inventory, overlap matrix, stack probe, remediations
  published) **and** a human merge grant covers that PR at its current head.
  Then MERGE_TRAIN **oldest `createdAt` first (bottom-up)**. Do not merge the
  first green PR. Zero unresolved `reviewThreads` (any author, paginated)
  immediately before each merge.

The grant is the human's act, never the agent's. The agent reports
MERGE_PENDING with the exact command; the **human** runs it in their own
terminal and types the target back to confirm:

```bash
# human only — merge_gate.py denies an agent that runs this or writes the grant file
"$HOME/.cursor-governance/.venv/bin/python" ops/autonomy/authorize_merge.py --repo {owner}/{repo} --pr {number} --head-sha {sha}
```

One grant per PR and head, expiring. `--all-open` is refused. A head that
moves after the grant returns the PR to MERGE_PENDING.

## Preferred — GitHub merge (stack-safe)

Do **not** choose `--squash` or `--merge` by hand. The helper probes whether
this head is the `baseRefName` of another open PR and emits the only safe
flags (`--merge` for a parent, `--squash` for a leaf). `--json` also reports
the live head and whether a human grant covers it (`AUTHORIZED` /
`MERGE_PENDING`); `--run` rechecks the live head, merges only under that
grant, and binds the merge to the SHA:

```bash
GOV_PY="${GOV_PY:-$PWD/.venv/bin/python}"
"$GOV_PY" ops/autonomy/stack_safe_merge.py --repo {owner}/{repo} --pr {number} --json
"$GOV_PY" ops/autonomy/stack_safe_merge.py --repo {owner}/{repo} --pr {number} --head-sha {sha} --run
```

Hand-typed `gh pr merge --squash` of a stack parent is denied by
`ops/autonomy/merge_gate.py` on Shell and MCP (unless human
`L9_STACK_CHECK_BYPASS` / `L9_MERGE_AUTHORIZED`).

Never `git merge origin/main` to "fix" a failing required check. After a
**parent squash**, never `gh pr update-branch` and never merge `main`
into the child. Rebase the child onto the new base:

```bash
git fetch origin
git rebase --onto origin/main <old-parent-tip> <child-branch>
```

Then publish the child with `PR_STACK=auto PR_REMEDIATE=0 make pr`. Direct bare `git push` is forbidden across all surfaces.

## Local merge when GitHub merge is infra-blocked

Do **not** check out `main` in the remediation worktree and `make pr` from
there — `make pr` refuses `main`/`master`.

```bash
# only when GitHub merge is blocked by infra AND the user asked to land locally
# stay on a feature branch; do not publish from main
```

Remediation publish is `PR_STACK=auto PR_REMEDIATE=0 make pr`. Direct bare `git push` is forbidden.

## Forbidden

- `git apply` / hand-copy from `gh pr diff` to adopt the PR
- Force-push to main
- `--admin` / bypass rules
- Merge during Diagnose (including “after user confirm” from Diagnose)
- Merge without a human grant for the PR's current head (CANONICAL_LAW §6.2.12)
- An agent running `authorize_merge.py`, writing `merge-authorization.json`, or enabling auto-merge
- Merge a red or conflicted PR
- Merge before FIRST_MERGE_GATE
- Squash/rebase a head that is the base of another open PR
- `gh pr update-branch` after squash-merging a parent
- Bare `git push` to an existing PR branch (remediation is published as a stacked PR via `make pr` — ADR-0052)
- Publish from the default branch (`make pr` refuses `main`/`master`)
