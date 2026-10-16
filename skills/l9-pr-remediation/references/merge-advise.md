<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: merge_advise
tags: [pr, merge, diagnose, git, stack-safe]
owner: igor_beylin
status: active
version: 2.4.0
updated: 2026-10-15
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
  (CANONICAL_LAW §6.2.13). A PR merges only when FIRST_MERGE_GATE holds
  (full open-PR inventory, overlap matrix, stack probe, remediations
  published) **and** human authorization covers that PR at its current
  head. Then MERGE_TRAIN **oldest `createdAt` first (bottom-up)**. Do not merge
  the first green PR. Zero unresolved `reviewThreads` (any author, paginated)
  immediately before each merge.

The authorization is the human's act, never the agent's. No terminal
transcription. Two records count (CANONICAL_LAW §6.2.13):

1. **GitHub.** The human submits an APPROVED review on the current head or
   posts this exact line on the pull request:

   ```text
   authorize merge {owner}/{repo}#{number}@{sha}
   ```

2. **Operator prompt.** The operator asked for the merge in their own words
   in chat — "merge these PRs", "fix and merge #{number} when green", "merge
   all open PR’s in https://github.com/{owner}/{repo}" — and the host prompt
   hook recorded it at submission (CANONICAL_LAW §6.2.14). Once
   the PR is green, mergeable and thread-clean, the agent transcribes it:

   ```bash
   "$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/ops/autonomy/authorize_merge.py" --operator-instruction --repo {owner}/{repo} --pr {number} --head-sha {sha}
   ```

   It refuses a moved head (re-run for the live head after readiness), a
   closed PR, a PR the instruction does not cover (a cohort covers only PRs
   open when it was spoken), and an operator without admin, maintain or write
   authority over the repository. The refusal names the
   prerequisite; it is MERGE_PENDING, not a reason to try another transport.

The operator may be the PR author and the PR may touch L9-ORG-007 paths: an
authorized owner's own instruction is the authorization (CANONICAL_LAW §6.2.14,
policy 4.0.0). Never ask them to repeat a recorded instruction, to use special
wording, or to post a GitHub comment. A head that moves after the record returns the PR to
MERGE_PENDING; a still-live instruction re-grants the verified final head
without asking the operator again. The agent does not post the line, does
not approve, and never writes the grant file or the instruction receipt.

## Preferred — GitHub merge (stack-safe)

Do **not** choose `--squash` or `--merge` by hand. The helper probes whether
this head is the `baseRefName` of another open PR and emits the only safe
flags (`--merge` for a parent, `--squash` for a leaf). `--json` also reports
the live head and whether human GitHub authorization covers it (`AUTHORIZED` /
`MERGE_PENDING`); `--run` rechecks the live head, merges only under that
grant, and binds the merge to the SHA:

```bash
# absolute paths: runs from any directory, consumer worktrees included
"$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/ops/autonomy/stack_safe_merge.py" --repo {owner}/{repo} --pr {number} --json
"$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/ops/autonomy/stack_safe_merge.py" --repo {owner}/{repo} --pr {number} --head-sha {sha} --run
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
- Merge without human authorization for the PR's current head (CANONICAL_LAW §6.2.13)
- An agent running the terminal mode of `authorize_merge.py`, writing `merge-authorization.json` or `operator-merge-instructions.json`, inventing an operator instruction, posting `authorize merge`, submitting an approving review, or enabling auto-merge
- Reporting a merge before `stack_safe_merge.py` prints `MERGED` with GitHub's merge commit
- Merge a red or conflicted PR
- Merge before FIRST_MERGE_GATE
- Squash/rebase a head that is the base of another open PR
- `gh pr update-branch` after squash-merging a parent
- Bare `git push` to an existing PR branch (remediation is published as a stacked PR via `make pr` — ADR-0052)
- Publish from the default branch (`make pr` refuses `main`/`master`)
