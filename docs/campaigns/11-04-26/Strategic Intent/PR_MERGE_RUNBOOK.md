# Explicit existing PRs | converge and merge if still open

The operator's latest instruction authorizes these three existing PRs as campaign merge subjects, conditional on latest-head readiness. CTO is the only session that merges. Coding agents own remediation and publication through the existing repo ceremony, not merge.

| PR | Exact scope | Observed 2026-11-17 | Required ordering |
|---|---|---|---|
| `.github#255` | v1 docs/candidates/ operator addition | open; `mergeable_state=blocked`; `mergeable=true`; head `922427b28e...` | independently converge, then merge before or with adoption |
| `Cursor-Governance#1011` | strategic-plan skill and registries | open; `unstable`; head `92a347ff7c...` | parent, merge first stack-safe |
| `Cursor-Governance#1030` | `/planner` mode and producer-generated projection bundles | open; `unstable`; head `5f175329a0...`; base `skills/l9-strategic-plan` | child, merge after proper parent integration and revalidation |

`.github#254` is an unrelated repository-registry PR observed open and blocked. It is **explicitly not in the authorized merge set**; if it merges independently, re-resolve current `main` and impacted bundle digests.

## CTO per-PR decision rule

1. Re-query LIVE current PR `state`, `merged`, head commit, base branch and `mergeable_state`. If already merged, inspect actual merge commit and diff, confirm expected approved scope and mark `ALREADY_MERGED_VERIFIED`. If closed unmerged, do not invent a new PR or recreate without operator decision.
2. A PR that says `mergeable=true` but `blocked` or `unstable` is NOT green. Require all required checks green on the exact live head, reviewer constraints and threads closed, no conflict, and all prescribed target checks satisfied. The child publishes and stands down. The CTO repairs a red check inside that lane's frozen write set. Lane A is the `.github` writer and publishes `#255` and the strategy adoption PR with `make pr`.
3. Resolve `ops/config/merge-authority.json` at the *current Cursor-Governance HEAD*. On the 2026-11-17 inspected main its enforcement is `disabled`, but this is NOT a permanent assumption; if it is now `strict`, follow `skills/l9-pr-remediation/SKILL.md` and active host-grant mechanisms and do not self-authorize.
4. Use only the current approved `ops/autonomy/stack_safe_merge.py` to merge, with `--repo`, `--pr`, and live `--head-sha`, in its documented `--run` mode. The command is recorded in the current source skill; verify it at the working host before execution. No `--admin`, force push, bypass, or manual GitHub merge pretending branch protection passed.
5. For #1011/#1030, preserve stacked commits; `stack_safe_merge.py` chooses the ancestry-safe merge method. After parent lands, retarget child to main only with a verified diff/ancestry check, and rerun all required head-specific CI/reviews before child merge. A retarget that drops generated receipts or a plugin manifest is a blocker.
6. After each merge, verify `main` includes the exact intended subjects, sha, and no forbidden changes. If PR head changed since approval and the change is material in Doctrine/Intent, the original exact approval is not enough.
7. The completion grant merges the three named PRs and every follow-on PR lanes A–D open inside their write scope. The trigger is campaign completion, passing CTO integration tests on a disposable combined worktree, and green required checks on that head. `.github#254`, a global `semantics/` change, a diff outside the lane write scope, and a red required check stay `MERGE_PENDING`. Do not disable enforcement or merge by bypass.

## Publication command boundary

Every lane publishes with one command, from that lane's checkout. `WS` selects the repo. `PR_BASE` is that PR's current base (`origin/main`, or `origin/skills/l9-strategic-plan` for `#1030` until `#1011` has merged). Leave `PR_STACK` empty. An already-open `make pr` does not change the GitHub base, and the gate diffs against `PR_BASE`, so the default `origin/main` is wrong for `#1030`.

```bash
PR_REMEDIATE=0 PR_BASE="origin/<this PR's current base>" \
  make -C "$HOME/.cursor-governance" pr WS="<this lane checkout>"
```

No raw `git push`, no direct `gh pr create`, no second ceremony per repo. After the command, the child writes `CTO-STATUS: stood-down` and does not remediate. The CTO merges only in the post-integration train.

## Merge train checkpoints

- **Train A:** `.github #255` current-head checks → stack-safe merge by CTO → verify candidate docs on `main` → separate exact `strategy/` operator adoption PR. Distinguish accepted candidate from adopted `strategy/` source at every stage.
- **Train C:** Cursor `#1011` current-head checks → merge **parent** with `stack_safe_merge.py` and observed ancestry → inspect `#1030` after parent merge; verify retarget/merge-base, projected receipts and full *child-only* diff → run current-head checks → merge child. Never silently squash an active stack parent or drop a child receipt.
- **Follow-on:** B and D PRs, when genuinely needed, are independent targets. They never auto-merge because the three named PRs were approved. Verify branch protections, required reviews and exact effective merge authority at merge time.

**`.github` publish:** Lane A runs the same `make pr` command with `WS` set to the `.github` checkout and `PR_BASE=origin/main`. `#255` and the strategy adoption PR wait for the same integration-test pass as the other in-scope PRs, then the CTO merges them in train order.
