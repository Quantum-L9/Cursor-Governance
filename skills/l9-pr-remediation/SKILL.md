---
name: l9-pr-remediation
description: diagnose or converge github prs — min preflight, remediate the open set, then a conflict-aware merge train. use when a campaign left prs unmergeable, the user invokes /l9-pr-remediation, or they ask to fix, remediate, babysit, converge, or merge failing prs.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, pr, ci, code-review, github-code-quality, copilot, diagnose, sonarcloud, codeql, debt, remediation, concurrent, github]
  owner: igor_beylin
  status: active
  version: 4.0.0
  updated: 2026-08-16
---

# PR Remediation

## Purpose

One pack, two intents: **Diagnose** (read-only readiness) or **Converge** (failing → green → merged). No packaging theater.

Converge is **REMEDIATE_ALL then MERGE_TRAIN**. It is not remediate-and-merge each PR as it turns green. [references/run-contract.md](references/run-contract.md).

| Intent | Mutates | Triggers | Behavior |
|--------|---------|----------|----------|
| **Diagnose** | no | review / readiness / blockers / `/pr` / “ready to merge?” | Fetch PR+reviews+CI; overlap advisory; slim verdict; **never** commit/push/merge |
| **Converge** | yes | `/l9-pr-remediation` / fix / remediate / babysit / merge failing PRs | Min preflight → remediate the open set → merge train |

Invoking this skill (or `/l9-pr-remediation`) **is** merge authorization for **all open PRs** in the target repo. Campaigns and `make pr` only publish. They do not merge. Load [references/merge-advise.md](references/merge-advise.md).

### Intent precedence (hard)

1. If `/l9-pr-remediation` or mutate language is present (`fix`, `remediate`, `babysit`, `push`, `merge` failing PRs, autonomy packet) → **Converge**.
2. Else if review/readiness/blockers/`/pr` → **Diagnose** only.
3. Ambiguous mixed ask without mutate verbs → **Diagnose**; ask one question before Converge.

## Target

All **open** PRs in the target `{owner}/{repo}`. A single `{owner}/{repo}#{pr}` argument still starts there, then continues through the remaining open PRs. Inventory the full set before the first merge. If no PR exists and Converge points at baseline debt/alerts: open a PR, then continue.

## Diagnose

Load [references/diagnose-workflow.md](references/diagnose-workflow.md). Optional focused lenses: [references/review-angles.md](references/review-angles.md). List unanswered **code-review agent** comments (`github-code-quality[bot]`, Copilot) as review blockers — [references/code-review-agents.md](references/code-review-agents.md). Report file-overlap across open PRs as advisory. Do not merge.

**Forbidden in Diagnose:** commit, push, force-push, edit worktree for fixes, alignment %, gap matrix, deep-eval, index theater, babysit loops.

## Converge — Inputs → Actions

| Signal | Source | Action |
|--------|--------|--------|
| CI failures | `gh run view --log-failed`, annotations | Fix codebase root cause |
| Review + inline | `gh api` reviews/comments | Validate against current code; fix or reply |
| Code-review agents | `github-code-quality[bot]`, Copilot review logins | Inspect **every** comment; fix if validated; reply to all — [references/code-review-agents.md](references/code-review-agents.md) |
| Workflows | `.github/workflows/*.yml` | Read-only gate discovery |
| SonarCloud | `scripts/sonar_fetch.py` | Lazy: only if configured **and** check failing / blocking. Output under `$PWD`. |
| CodeQL | `scripts/codeql_fetch.py` | Lazy: only if check failing or alerts open |
| Lint/type/test/build debt | `scripts/debt_audit.py` + repo toolchain | Lazy: only if toolchain/baseline red |

## Converge — Outputs (per PR that changes code)

- One `RUN_CONTRACT` for the run (first status; reuse until invalidated)
- One structured remediation plan (inline ledger) per PR being edited
- One commit, one sanctioned publish (success path)
- Canonical replies on every thread; all threads resolved
- Short convergence status with timing counters

No tarballs, run-report schemas, issue-file bundles, or exemplary packaging.

## Authority Order

1. Latest user instruction and explicit PR/scope
2. Current repository source and tests
3. Required-check logs and branch-protection evidence
4. Human review, then **code-review agents** (`github-code-quality[bot]`, Copilot), then other blocking bots, then newer/higher-confidence comments
5. Scanner API evidence confirmed against current source
6. This skill + references
7. Unknown — do not invent; note and continue independent work

## Laws (Converge)

1. **Min preflight, then execute.** Required once: command surface, venv fingerprint, PR inventory + overlap, known blockers, verify path. Emit `RUN_CONTRACT` and reuse it. Do not re-census the fleet. Per-PR finding ingest covers only the PR about to be edited. Lazy Sonar/CodeQL/debt unless that check is failing or configured-and-blocking. Resume discovery on unexpected failure, scope change, env drift, or topology change. [references/run-contract.md](references/run-contract.md).
2. **One-and-done per PR, then a safety valve.** Success path is **one** plan, **one** commit, **one** CI run per PR. Max three cycles; never start cycle 4. Extra cycles are only for signals that did not exist at plan time.
3. **Codebase only.** Repair source, tests, fixtures, package deps. Never edit `.github/workflows/**`, actions, runners, permissions, secrets, OIDC, branch protection, check wiring, or CI-only infra. Pipeline blockers: record one line in the status and keep remediating everything else.
4. **Ownership before edit.** Load [references/ownership-boundary.md](references/ownership-boundary.md). Edit only `CODEBASE`. `ENVIRONMENT` (interpreter/arch/ABI/venv) is not a code defect — run the venv preflight once and continue.
5. **Plan the PR, then patch that PR.** No edits on a PR until its ingested findings have dispositions. Independent clusters run in parallel into one worktree batch. A locked `Remediation-Cycle` / plan whose files still match is executed, not rewritten.
6. **One commit, one sanctioned publish.** Zero if nothing codebase-safe remains. Never commit-per-finding, never publish to probe CI, never `--no-verify`. Never raw `git push` when the cached publish target is `make pr`.
7. **Local verify blocks commit.** Run the Makefile primary gate when a Makefile exists. Also run the relevant hook/compiler on **cited and planned paths** even when the default toolchain excludes them. Do not require all-files pre-commit. Never `--no-verify`. Remote CI confirms; it does not discover.
8. **Short poll.** After publish: poll every **15s** (or `gh run watch`); max **8 minutes** per cycle. Do not idle. A green SHA stays valid until HEAD, a required check, or a new thread changes.
9. **Validate suggestions against current code.** Comment snippets are not ground truth.
10. **No gate weakening / suppressions.** No `NOSONAR`, blanket noqa/type-ignore/eslint-disable, CodeQL dismissals/exclusions, skipped tests, or lowered thresholds. Narrow documented suppression only for a *proven* false positive where a code fix is less safe.
11. **Every conversation resolved.** Reply Fixed / Deferred / Acknowledged / Disagreed, then `resolveReviewThread` on **every** GraphQL `reviewThreads` node with `isResolved: false` — any author (`github-code-quality`, Copilot, `github-advanced-security`, CodeQL, humans, unknown bots). GitHub "a conversation must be resolved" **is** a merge blocker. HUMAN: name the decision in the reply (linked issue if Deferred), resolve the thread, **do not merge that PR** until the decision exists. Bots re-file on new lines after a push — those are **new** threads. Re-query after every publish and immediately before `gh pr merge`.
12. **FIRST_MERGE_GATE.** Never force-push, rewrite history, expose tokens, or `--admin` merge. Ordinary `gh pr merge --squash` is the merge verb — **only after** the open-PR inventory, overlap matrix, and merge-effect prediction exist, and after the required sequence is remediated and published. Do not merge the first green PR. Do not merge oldest-`createdAt`-first by default. After an authorized train merge, `gh pr update-branch` only remaining PRs whose overlap predicted a material effect. Revalidate CI only when HEAD changed.
13. **Scanner closure is remote.** Local fix ≠ Sonar/CodeQL closed until the exact head SHA is green remotely (`PENDING_REMOTE_ANALYSIS` otherwise). Fetch scripts are read-only; write outputs under `$PWD`. Never mutate remote issue/alert state.

## Hot Path (Converge)

0. **Authorize + min preflight (once).** Write the repo-scoped receipt. Load [references/run-contract.md](references/run-contract.md). Discover and **cache** the sanctioned command surface. Fingerprint the venv (`UV_PYTHON` native CPython; reject x86_64/miniconda on arm64). List **all** open PRs and build the overlap matrix (`gh pr view --json files`). Bootstrap the worktree (not detached; wire without committing `AGENTS.md`). Emit `RUN_CONTRACT`.

```bash
python3 ops/autonomy/authorize_merge.py --repo {owner}/{repo} --all-open \
  --reason "l9-pr-remediation invoked"
gh pr list --repo {owner}/{repo} --state open \
  --json number,createdAt,mergeable,headRefName,baseRefName,statusCheckRollup
```

Reuse a locked plan / `Remediation-Cycle:` trailer when files still match. If no PR and the user wants baseline debt/alerts fixed: create branch, remediate, open PR via the sanctioned publish target, continue.

1. **Discover gates (read-only).** Parse `Makefile` for `pr` / `pr-check` / `open_pr_after_gate`. If `pr` exists, cached publish is `PR_REMEDIATE=0 make pr`. Never probe `git push`. Parse leftover workflow `run:` commands. Do not edit CI surfaces.
2. **Ingest the PR about to be edited.** Failed CI + annotations, human reviews, every bot comment, every CRA thread. Sonar/CodeQL/debt only when failing or configured-and-blocking. [references/signal-ingestion.md](references/signal-ingestion.md) + [references/code-review-agents.md](references/code-review-agents.md).
3. **Classify + write that PR's plan.** Ownership then severity; companions if touching `pec/*`, `skills/*`, or `rules/*`. [references/finding-classifier.md](references/finding-classifier.md) + [references/remediation-plan.md](references/remediation-plan.md).
4. **Fix the planned batch.** All `disposition: fix` clusters. Skip HUMAN / CI_PIPELINE / ENVIRONMENT (note them). [references/fix-engine.md](references/fix-engine.md). Independent PRs may be remediated in parallel after the overlap matrix exists. Do not commit yet. Do not merge yet.
5. **Local verify (blocks commit).** Makefile primary (`pr-check` / `agent-check` / `check` / `ci` / `validate`) with cached `UV_PYTHON`. Plus cited/planned paths. ≤5 iterations. Never `--no-verify`.
6. **One commit, one sanctioned publish.** Explicit `git add` of planned files only. Never `git add -u` / `-A`. Never `git reset --hard`. Publish with the cached target (`PR_REMEDIATE=0 make pr` on this host). Trailer `Remediation-Cycle: {repo}#{pr}/cycle-1`. Poll workers never merge. Ignore `merge_eligible` whose SHA is older than HEAD or older than the last repo merge.
7. **Reply + resolve.** Every thread, any author. [references/review-replies.md](references/review-replies.md).
8. **Short-poll that SHA.** [references/convergence-loop.md](references/convergence-loop.md). Re-query `reviewThreads`. Reply + resolve re-files. **Do not merge** because this one PR is green. Repeat 2–8 for remaining in-scope PRs.
9. **MERGE_TRAIN** only after FIRST_MERGE_GATE. Immediately before each `gh pr merge`, re-query `reviewThreads`. Zero `isResolved: false` required.

```bash
gh pr merge {n} --repo {owner}/{repo} --squash --delete-branch
# then only for remaining PRs with predicted material overlap:
gh pr update-branch {rest} --repo {owner}/{repo}
```

Never `--admin`. Never unpack diffs. Never merge-as-you-go. An unpredicted `CONFLICTING` after a merge means the overlap preflight failed — rebuild the remaining matrix before the next merge.

## Done When (Converge)

On the final observed head SHA of each open PR, then after the train (or a documented independence merge):

- required checks success (or only recorded CI-pipeline / ENVIRONMENT / HUMAN blockers remain — those PRs stay unmerged)
- no unpredicted merge conflict
- no unresolved GraphQL `reviewThreads` (any author)
- Sonar/CodeQL/debt: confirmed codebase root causes fixed when those surfaces were in scope; remote scanner closure claimed only when observed
- green mergeable PRs in the train are **merged**
- worktree clean
- status names remaining blockers and the six timing counters

## Generated-artifact merge contract (PR_OVERLAP_GUARDRAIL_V1)

- After any merge that touched generated paths — or whenever
  `.l9/pr/regen-required.txt` is non-empty (written by the `merge=l9-generated`
  driver) — run `python3 ops/scripts/sync_generated_artifacts.py --force`,
  stage, and commit before opening or updating a PR. A merge is not complete
  while the marker lists paths.
- Same-agent overlapping work routes into the existing open PR branch (one
  commit, one PR) instead of opening a sibling PR against main. The pre-open
  overlap gate (`ops/scripts/pr_overlap_check.py`, run by `make pr`) blocks
  sibling PRs that would textually conflict; generated paths are exempt
  because regeneration heals them.
- See `rules/53-pr-overlap-guardrail.mdc`.

## Resource Map

### Diagnose
- [references/diagnose-workflow.md](references/diagnose-workflow.md)
- [references/code-review-agents.md](references/code-review-agents.md)
- [references/review-angles.md](references/review-angles.md)
- [references/merge-advise.md](references/merge-advise.md)
- [references/run-contract.md](references/run-contract.md)

### Converge
- [references/run-contract.md](references/run-contract.md) — preflight, cache, venv, topology, publish surface
- [references/ownership-boundary.md](references/ownership-boundary.md)
- [references/remediation-plan.md](references/remediation-plan.md)
- [references/signal-ingestion.md](references/signal-ingestion.md)
- [references/finding-classifier.md](references/finding-classifier.md)
- [references/fix-engine.md](references/fix-engine.md)
- [references/code-review-agents.md](references/code-review-agents.md)
- [references/review-replies.md](references/review-replies.md)
- [references/convergence-loop.md](references/convergence-loop.md)
- [references/validation-gates.md](references/validation-gates.md)
- [references/sonarcloud-remediation.md](references/sonarcloud-remediation.md)
- [references/debt-remediation.md](references/debt-remediation.md)
- [references/codeql-remediation.md](references/codeql-remediation.md)
- [scripts/sonar_fetch.py](scripts/sonar_fetch.py)
- [scripts/debt_audit.py](scripts/debt_audit.py)
- [scripts/codeql_fetch.py](scripts/codeql_fetch.py)
- [scripts/self_test.py](scripts/self_test.py)

## Defaults

```yaml
max_cycles: 3
one_and_done: true
max_local_verify_iterations: 5
poll_interval_seconds: 15
max_wait_per_cycle_minutes: 8
parallel_clusters: true
parallel_independent_prs: true   # after overlap matrix; never parallelize merge
ci_pipeline_policy: note_and_skip
publish: PR_REMEDIATE=0 make pr  # when Makefile pr exists
local_verify:
  prefer_makefile: true
  cited_paths_required: true
  require_precommit_all_files: false
  forbid_no_verify: true
merge:
  first_merge_gate: true
  oldest_created_at_default: false
```

## Failure Handling

### Diagnose
- PR number missing → STOP; ask or list open PRs
- Skip review comments → BLOCK verdict; fetch comments first
- CI logs unavailable → note `Unknown` for CI; still report reviews/blockers

### Converge
- Native-ext / cryptography import fail → `ENVIRONMENT`; run venv preflight once; do not edit source; do not unpin lock pins; do not symlink a failing SSOT venv
- `git push` denied with `make pr` in the message → cache publish=`PR_REMEDIATE=0 make pr`; do not retry `git push`
- `git add -u` / `reset --hard` denied → stage explicit paths only
- CI logs missing → retry annotations/job logs once; if ownership unknown, note and continue other clusters
- Rate limit → honor reset, retry once, continue
- Fix breaks a gate → revert that fix, defer with reason, keep the rest of the batch (still one commit)
- Partial publish to probe CI → protocol violation
- Local green / remote red → classify ownership; environment delta or new post-push comments → next cycle; unrun local gate → protocol failure
- Scanner identity/pagination/path-blocked → stop that scanner cluster; continue others (do not block Converge when that check is green)
- Poll worker `merge_eligible` on a stale SHA → ignore; never merge from it
- Unpredicted `CONFLICTING` after a merge → rebuild remaining overlap; do not continue the train blindly
- Max cycles → report remaining items; do not start cycle 4

## Final Status (required)

### Diagnose
Verdict · blockers · warnings · key review concerns · overlap advisory · YNP

### Converge
`RUN_CONTRACT` summary · plan finding counts · commits this PR (must be 1 on success) · Makefile result · head SHA · CI result · fixed clusters · PRs merged · remaining open PRs · remaining CODEBASE / CI_PIPELINE / HUMAN / ENVIRONMENT blockers · scanner pending-remote if any · counters:

- `time_to_first_useful_action`
- `blocked_command_attempts`
- `environment_repair_count`
- `ci_run_count`
- `merge_conflict_count`
- `repeated_command_count`

## Validation

```bash
python3 scripts/self_test.py
```
