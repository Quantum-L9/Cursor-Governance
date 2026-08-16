---
name: l9-pr-remediation
description: diagnose or converge github prs — census every ci/human/bot/copilot/github-code-quality signal, plan, then one makefile+pre-commit-validated commit and merge. use when a campaign left prs unmergeable, the user invokes /l9-pr-remediation, or they ask to fix, remediate, babysit, converge, or merge failing prs.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, pr, ci, code-review, github-code-quality, copilot, diagnose, sonarcloud, codeql, debt, remediation, concurrent, github]
  owner: igor_beylin
  status: active
  version: 3.4.0
  updated: 2026-08-16
---

# PR Remediation

## Purpose

One pack, two intents: **Diagnose** (read-only readiness) or **Converge** (failing → green → merged). No packaging theater. Converge remains one path, max depth.

**One-and-done:** full census of every CI / human / bot / Copilot / Code Quality signal → structured plan that tracks each finding → fix the whole codebase batch → Makefile + every `.pre-commit-config.yaml` hook green → **one commit, one push**. Plan first so remote CI runs once. [references/remediation-plan.md](references/remediation-plan.md).

| Intent | Mutates | Triggers | Behavior |
|--------|---------|----------|----------|
| **Diagnose** | no | review / readiness / blockers / `/pr` / “ready to merge?” | Fetch PR+reviews+CI; slim verdict; optional review angles; YNP; **never** commit/push/merge |
| **Converge** | yes | `/l9-pr-remediation` / fix / remediate / babysit / merge failing PRs | Hot path below; **then merge** every green mergeable open PR |

Invoking this skill (or `/l9-pr-remediation`) **is** merge authorization for **all open PRs** in the target repo. Campaigns and `make pr` only publish green merge-ready PRs; they do not merge. Load [references/merge-advise.md](references/merge-advise.md).

### Intent precedence (hard)

1. If `/l9-pr-remediation` or mutate language is present (`fix`, `remediate`, `babysit`, `push`, `merge` failing PRs, autonomy packet) → **Converge**. A full Diagnose **census** is mandatory cycle-0 inside Converge (no edits until the plan is written); do not stop at advise-only.
2. Else if review/readiness/blockers/`/pr` → **Diagnose** only.
3. Ambiguous mixed ask without mutate verbs → **Diagnose**; ask one question before Converge.

## Target

All **open** PRs in the target `{owner}/{repo}` (bottom-up by `createdAt`). A single `{owner}/{repo}#{pr}` argument still starts there, then continues through the remaining open PRs. If no PR exists and Converge points at baseline debt/alerts: open a PR, then continue.

## Diagnose

Load [references/diagnose-workflow.md](references/diagnose-workflow.md). Optional focused lenses: [references/review-angles.md](references/review-angles.md). List unanswered **code-review agent** comments (`github-code-quality[bot]`, Copilot) as review blockers — [references/code-review-agents.md](references/code-review-agents.md).

**Forbidden in Diagnose:** commit, push, force-push, edit worktree for fixes, alignment %, gap matrix, deep-eval, index theater, babysit loops.

## Converge — Inputs → Actions

| Signal | Source | Action |
|--------|--------|--------|
| CI failures | `gh run view --log-failed`, annotations | Fix codebase root cause |
| Review + inline | `gh api` reviews/comments | Validate against current code; fix or reply |
| Code-review agents | `github-code-quality[bot]`, Copilot review logins | Inspect **every** comment; fix if validated; reply to all — [references/code-review-agents.md](references/code-review-agents.md) |
| Workflows | `.github/workflows/*.yml` | Read-only gate discovery |
| SonarCloud | `scripts/sonar_fetch.py` | Confirm vs source; fix clusters |
| CodeQL | `scripts/codeql_fetch.py` | Dataflow-confirm; fix + negative test |
| Lint/type/test/build debt | `scripts/debt_audit.py` + repo toolchain | Fix baseline + regressions |

## Converge — Outputs (per PR that changes code)

- One structured remediation plan (inline ledger)
- One commit, one push (success path)
- Canonical replies on every thread
- Short convergence status (what fixed, what remains, CI note)

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

1. **One path, max depth.** Always ingest CI + reviews + Sonar (if configured/failing) + CodeQL (if failing/open) + debt (if baseline/toolchain red). No dry-run / audit-first / security / CI-signal modes.
2. **One-and-done, then a safety valve.** Success path is **one** census, **one** plan, **one** commit, **one** CI run. Max three cycles; never start cycle 4. Extra cycles are only for signals that did not exist at census time — not for a skipped census or a partial batch. [references/remediation-plan.md](references/remediation-plan.md).
3. **Codebase only.** Repair source, tests, fixtures, package deps. Never edit `.github/workflows/**`, actions, runners, permissions, secrets, OIDC, branch protection, check wiring, or CI-only infra. Pipeline blockers: record one line in the status and keep remediating everything else.
4. **Ownership before edit.** Load [references/ownership-boundary.md](references/ownership-boundary.md). Edit only codebase-owned defects.
5. **Plan before patch.** No edits until every ingested finding has a disposition on the plan. Independent clusters then run in parallel and merge into one worktree batch.
6. **One commit, one push.** Zero if nothing codebase-safe remains. Never commit-per-finding, never push to probe CI, never `--no-verify`.
7. **Local verify blocks commit.** Run the Makefile primary gate **and** every hook in `.pre-commit-config.yaml` (when those files exist); then any leftover workflow `run:` commands. Fix until green (≤5 re-diag iterations). Remote CI confirms; it does not discover.
8. **Short poll.** After push: poll every **15s** (or `gh run watch`); max **8 minutes** per cycle. Do not idle.
9. **Validate suggestions against current code.** Comment snippets are not ground truth.
10. **No gate weakening / suppressions.** No `NOSONAR`, blanket noqa/type-ignore/eslint-disable, CodeQL dismissals/exclusions, skipped tests, or lowered thresholds. Narrow documented suppression only for a *proven* false positive where a code fix is less safe.
11. **Every thread answered.** Reply Fixed / Deferred / Acknowledged / Disagreed. Resolve when done; leave true human-decision threads open with the decision named. **Code-review agent** comments (`github-code-quality[bot]`, Copilot) are never skippable chatter: inspect, analyze, fix if validated, reply to all. Volume, Note severity, and `skip_bot_discussions` do not exempt them.
12. **Never** force-push, rewrite history, expose tokens, or `--admin` merge. Ordinary `gh pr merge --squash` **is required** after Converge on each green mergeable open PR in the target repo.
13. **Scanner closure is remote.** Local fix ≠ Sonar/CodeQL closed until the exact head SHA is green remotely (`PENDING_REMOTE_ANALYSIS` otherwise). Fetch scripts are read-only; never mutate remote issue/alert state.

## Hot Path (Converge)

0. **Authorize + resolve.** Write the repo-scoped receipt, then list open PRs oldest first:

```bash
python3 ops/autonomy/authorize_merge.py --repo {owner}/{repo} --all-open \
  --reason "l9-pr-remediation invoked"
gh pr list --repo {owner}/{repo} --state open --json number,createdAt,mergeable,statusCheckRollup
```

Reuse prior cycle markers if present (`Remediation-Cycle:` trailer, `<!-- l9-remediation:... -->` replies). If no PR and the user wants baseline debt/alerts fixed: create branch, remediate, open PR, continue.
1. **Discover gates (read-only).** Parse `Makefile`, `.pre-commit-config.yaml` (every hook `id`), workflows, and package scripts into the verify list. Do not edit CI surfaces.
2. **Full census (no edits).** Ingest every signal in parallel — failed CI + annotations, human reviews, **every** bot comment, **every** `github-code-quality[bot]` and Copilot thread, Sonar/CodeQL/debt when configured or failing. [references/diagnose-workflow.md](references/diagnose-workflow.md) + [references/signal-ingestion.md](references/signal-ingestion.md) + [references/code-review-agents.md](references/code-review-agents.md).
3. **Classify + write the plan (blocks edits).** Ownership then severity; cluster by root cause; give every finding a disposition. [references/finding-classifier.md](references/finding-classifier.md) + [references/remediation-plan.md](references/remediation-plan.md). Do not patch until the plan gate passes.
4. **Fix the full planned batch concurrently.** All `disposition: fix` clusters. Skip only true human-product forks and CI-pipeline surfaces (note them on the plan). [references/fix-engine.md](references/fix-engine.md) (**Lesson Recall** before inventing a patch). Do not commit yet.
5. **Local verify (blocks commit).** `pre-commit run --all-files` when `.pre-commit-config.yaml` exists; the Makefile primary target (`agent-check` / `pr-check` / `check` / `ci` / `validate`) when a Makefile exists; then leftover workflow commands. Re-run all on any fix. ≤5 iterations. Never `--no-verify`.
6. **One commit, one push.** Conventional message; trailer `Remediation-Cycle: {repo}#{pr}/cycle-1`. No second commit to probe CI.
7. **Reply.** Canonical replies on every thread, including every code-review agent comment. [references/review-replies.md](references/review-replies.md) + [references/code-review-agents.md](references/code-review-agents.md).
8. **Short-poll + decide.** [references/convergence-loop.md](references/convergence-loop.md). If green and no new post-push signals → merge that PR, then the next older-to-newer open PR. A second cycle is allowed only for signals that did not exist at census time, and only if cycles < 3. If only CI-pipeline / human blockers remain → stop early (do not merge that PR).
9. **Merge.** For each PR that is green + mergeable, with no unanswered codebase or code-review agent threads:

```bash
gh pr merge {n} --repo {owner}/{repo} --squash --delete-branch
```

Never `--admin`. Never unpack diffs. Oldest `createdAt` first.

## Done When (Converge)

On the final observed head SHA of each open PR, then after merge:

- required checks success (or only recorded CI-pipeline blockers remain — those PRs stay unmerged)
- no merge conflict; review not requesting changes from unaddressed codebase items
- no unanswered review threads, including every code-review agent comment (`github-code-quality[bot]`, Copilot)
- Sonar/CodeQL/debt: confirmed codebase root causes fixed; remote scanner closure claimed only when observed
- green mergeable PRs are **merged**
- worktree clean
- status names remaining CI-pipeline and human blockers (if any)

## Resource Map

### Diagnose
- [references/diagnose-workflow.md](references/diagnose-workflow.md)
- [references/code-review-agents.md](references/code-review-agents.md)
- [references/review-angles.md](references/review-angles.md)
- [references/merge-advise.md](references/merge-advise.md)

### Converge
- [references/diagnose-workflow.md](references/diagnose-workflow.md) — mandatory census before the plan
- [references/ownership-boundary.md](references/ownership-boundary.md) — codebase vs CI vs human
- [references/remediation-plan.md](references/remediation-plan.md) — census → plan → Makefile/pre-commit → one commit
- [references/signal-ingestion.md](references/signal-ingestion.md)
- [references/finding-classifier.md](references/finding-classifier.md)
- [references/fix-engine.md](references/fix-engine.md) — includes lesson recall against `learning/failures/repeated-mistakes.md` + `learning/patterns/quick-fixes.md`
- [references/code-review-agents.md](references/code-review-agents.md) — `github-code-quality[bot]` + Copilot: inspect / fix-if-valid / reply-all
- [references/review-replies.md](references/review-replies.md)
- [references/convergence-loop.md](references/convergence-loop.md) — 15s poll, early stop
- [references/validation-gates.md](references/validation-gates.md) — inline cycle proofs (not deliverables)
- [references/sonarcloud-remediation.md](references/sonarcloud-remediation.md)
- [references/debt-remediation.md](references/debt-remediation.md)
- [references/codeql-remediation.md](references/codeql-remediation.md)
- [scripts/sonar_fetch.py](scripts/sonar_fetch.py)
- [scripts/debt_audit.py](scripts/debt_audit.py)
- [scripts/codeql_fetch.py](scripts/codeql_fetch.py)

## Defaults

```yaml
max_cycles: 3                    # safety valve only; success path is 1 commit
one_and_done: true
max_local_verify_iterations: 5
poll_interval_seconds: 15
max_wait_per_cycle_minutes: 8
parallel_clusters: true
ci_pipeline_policy: note_and_skip  # never edit; no issue-file packaging
local_verify:
  prefer_makefile: true
  require_precommit_all_hooks: true
  forbid_no_verify: true
```

## Failure Handling

### Diagnose
- PR number missing → STOP; ask or list open PRs
- Skip review comments → BLOCK verdict; fetch comments first
- CI logs unavailable → note `Unknown` for CI; still report reviews/blockers

### Converge
- CI logs missing → retry annotations/job logs once; if ownership unknown, note and continue other clusters
- Rate limit → honor reset, retry once, continue
- Fix breaks a gate → revert that fix, defer with reason, keep the rest of the batch (still one commit)
- Partial commit/push to probe CI → protocol violation; do not add more commits to "catch up"
- Local green / remote red → classify ownership; environment delta or new post-push comments → next cycle; skipped census / unrun local gate → protocol failure, fix locally and only then a second commit if still needed
- Local green / remote red (pipeline) → note and stop cycling on that item
- Scanner identity/pagination blocked → stop that scanner cluster; continue others
- Max cycles → report remaining items; do not start cycle 4

## Final Status (required)

### Diagnose
Verdict · blockers · warnings · key review concerns · YNP

### Converge
Census complete · plan finding counts · commits this PR (must be 1 on success) · Makefile/pre-commit result · head SHA · CI result · fixed clusters · PRs merged · remaining open PRs · remaining codebase / CI-pipeline / human blockers · scanner pending-remote if any.
