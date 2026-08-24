---
name: ff
version: "1.0.0"
description: "Fast-forward safely — fetch, prove branch novelty by patch id and line absorption, publish what is genuinely novel via make pr, then fast-forward and prune the proven-redundant"
skill: l9-git-work-preserve
auto_chain: ynp
---

# /ff — Prove, publish, fast-forward, prune

Delegates to skill **`l9-git-work-preserve`**. Operates on the repo in the
current working directory.

The order is the whole point: **nothing is fast-forwarded or deleted until every
branch has been classified against a freshly fetched baseline.** A branch that
still holds unlanded work is published first, never pruned.

## WHAT IT DOES

| Step | Action | Mutates? |
|------|--------|----------|
| 1 | Fetch origin; classify every local branch | No |
| 2 | Hand off genuinely novel branches to `make pr` | Opens PRs |
| 3 | Fast-forward the baseline branch | Local |
| 4 | `git branch -d` the proven-redundant | Local |

Classification comes from `diagnose_ref_value.py` and is evidence-based, not a
commit count — see [value-diagnosis.md](../skills/l9-git-work-preserve/references/value-diagnosis.md):

| Bucket | Class | Meaning |
|--------|-------|---------|
| `novel` | `keep_push` | Holds work not accounted for upstream → publish |
| `superseded` | `archive_ref` | Work landed by patch id or line absorption → prune |
| `merged` | `prune_candidate` | Zero commits ahead → prune |
| `unproven` | `unknown` | Baseline unresolvable → keep, report |

## EXECUTION

1. Load skill `l9-git-work-preserve`.
2. `python3 skills/l9-git-work-preserve/scripts/ff_pipeline.py --repo "$(pwd)" --mode plan`
3. **If `blocked`** — a dirty tree stops here. Dirt is `/clean`'s job to route;
   do not stage, stash, or discard it to get past this gate.
4. **If `novel` is empty** — skip step 5 entirely. Do not run the L4 sequence and
   do not call `make pr`; there is nothing to publish and an empty PR is noise.
5. **For each novel branch**, in order:
   ```bash
   git switch <branch>
   make -C "$GOV_ROOT" l4-begin WS="$(pwd)"
   # apply kernels/Recursive Alignment.md, then kernels/Validate & Repair.md
   make -C "$GOV_ROOT" improve IMPROVE_RECORD=1 WS="$(pwd)"
   PR_REMEDIATE=0 make -C "$GOV_ROOT" pr WS="$(pwd)"
   ```
   `l4-begin` is required **per branch**: after the first `make pr` the phase is
   `release_authorized` for that branch, `improve` will not re-begin, and
   `authorize-release` raises branch drift on the next one.
6. `ff_pipeline.py --repo "$(pwd)" --mode apply` — fast-forward, then prune.
7. Report `needs_human[]` verbatim. Each entry carries a tip SHA and the exact
   `git branch -D` command; the user runs it, not the agent.
8. Auto-chain `/ynp`.

## WHAT A PR DOES NOT DO

`make pr` **opens** a PR; it does not merge. So work published in step 5 is not
in `origin/main` when step 6 fast-forwards, and its branch is deliberately left
alive. Merging is `/l9-pr-remediation`, a separate authority — invoking it
authorizes merge of *all* open PRs in the repo, so `/ff` never calls it.

## FORBIDDEN

- Raw `git push`, `gh pr create`, `make push`, or MCP `create_pull_request` —
  `make pr` is the only sanctioned route to GitHub because it is the only one
  that runs the checkers
- `git branch -D` or `git push --delete` on the user's behalf — force-delete is
  `prune-execute` under [prune-policy.md](../skills/l9-git-work-preserve/references/prune-policy.md)
- Fast-forwarding or pruning before every branch is classified
- Clearing a dirty tree to get past the block
- Deleting a branch checked out in another worktree
- Treating `fetched: false` as proof of anything
