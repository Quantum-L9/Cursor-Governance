<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: pr_landing
tags: [issues, pr, stack, make_pr]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-29
/L9_META -->

# PR landing rule

`make_pr: true` means the fix is on a GitHub PR. It does **not** mean “always
run `make pr`.” Use `scripts/pr_landing.py`.

After local verify, in the **owning** repo:

1. **Belong on an existing open PR** — same repo, and the open PR already owns
   that cluster / path / issue (`Fixes #n`, `Fixes owner/repo#n`, or overlapping
   changed files). Commit and `git push` onto **that** branch. Do not open a
   sibling PR. This is remediator-publish, not a second `make pr`.
2. **Otherwise** — open a **new stacked PR on the newest open PR**
   (`PR_STACK=auto`). `PR_REMEDIATE=0 make pr`. PR body lists `Fixes #n` /
   `Fixes owner/repo#n` for every issue in the cluster. Trailer:
   `Issue-Remediation-Cycle: {owner}/{repo}#{n}/cycle-{N}`.
3. **No open PRs** — first PR against `origin/main` (`PR_STACK=`).
4. Sibling open-PR chains still fail closed. Do not invent a second stack.

Never `gh pr merge` from this skill.
