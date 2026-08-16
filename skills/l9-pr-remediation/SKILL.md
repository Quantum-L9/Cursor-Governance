---
name: l9-pr-remediation
description: diagnose or converge github prs — read-only status/review, or remediate ci/review/scanner/debt to green then merge all open prs in the target repo. use when a campaign left prs unmergeable, the user invokes /l9-pr-remediation, or they ask to fix, remediate, babysit, converge, or merge failing prs.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, pr, ci, code-review, diagnose, sonarcloud, codeql, debt, remediation, concurrent, github]
  owner: igor_beylin
  status: active
  version: 3.2.0
  updated: 2026-08-16
---

# PR Remediation

## Purpose

One pack, two intents: **Diagnose** (read-only readiness) or **Converge** (failing → green → merged). No packaging theater. Converge remains one path, max depth.

| Intent | Mutates | Triggers | Behavior |
|--------|---------|----------|----------|
| **Diagnose** | no | review / readiness / blockers / `/pr` / “ready to merge?” | Fetch PR+reviews+CI; slim verdict; optional review angles; YNP; **never** commit/push/merge |
| **Converge** | yes | `/l9-pr-remediation` / fix / remediate / babysit / merge failing PRs | Hot path below; **then merge** every green mergeable open PR |

Invoking this skill (or `/l9-pr-remediation`) **is** merge authorization for **all open PRs** in the target repo. Campaigns and `make pr` only publish green merge-ready PRs; they do not merge. Load [references/merge-advise.md](references/merge-advise.md).

### Intent precedence (hard)

1. If `/l9-pr-remediation` or mutate language is present (`fix`, `remediate`, `babysit`, `push`, `merge` failing PRs, autonomy packet) → **Converge** (Diagnose may run as cycle-0 status inside Converge, but must not stop at advise-only).
2. Else if review/readiness/blockers/`/pr` → **Diagnose** only.
3. Ambiguous mixed ask without mutate verbs → **Diagnose**; ask one question before Converge.

## Target

All **open** PRs in the target `{owner}/{repo}` (bottom-up by `createdAt`). A single `{owner}/{repo}#{pr}` argument still starts there, then continues through the remaining open PRs. If no PR exists and Converge points at baseline debt/alerts: open a PR, then continue.

## Diagnose

Load [references/diagnose-workflow.md](references/diagnose-workflow.md). Optional focused lenses: [references/review-angles.md](references/review-angles.md).

**Forbidden in Diagnose:** commit, push, force-push, edit worktree for fixes, alignment %, gap matrix, deep-eval, index theater, babysit loops.

## Converge — Inputs → Actions

| Signal | Source | Action |
|--------|--------|--------|
| CI failures | `gh run view --log-failed`, annotations | Fix codebase root cause |
| Review + inline | `gh api` reviews/comments | Validate against current code; fix or reply |
| Workflows | `.github/workflows/*.yml` | Read-only gate discovery |
| SonarCloud | `scripts/sonar_fetch.py` | Confirm vs source; fix clusters |
| CodeQL | `scripts/codeql_fetch.py` | Dataflow-confirm; fix + negative test |
| Lint/type/test/build debt | `scripts/debt_audit.py` + repo toolchain | Fix baseline + regressions |

## Converge — Outputs (per cycle that changes code)

- One commit, one push
- Canonical replies on touched threads
- Short convergence status (what fixed, what remains, CI note)

No tarballs, run-report schemas, issue-file bundles, or exemplary packaging.

## Authority Order

1. Latest user instruction and explicit PR/scope
2. Current repository source and tests
3. Required-check logs and branch-protection evidence
4. Human review, then blocking bots, then newer/higher-confidence comments
5. Scanner API evidence confirmed against current source
6. This skill + references
7. Unknown — do not invent; note and continue independent work

## Laws (Converge)

1. **One path, max depth.** Always ingest CI + reviews + Sonar (if configured/failing) + CodeQL (if failing/open) + debt (if baseline/toolchain red). No dry-run / audit-first / security / CI-signal modes.
2. **Max three cycles.** Never start cycle 4.
3. **Codebase only.** Repair source, tests, fixtures, package deps. Never edit `.github/workflows/**`, actions, runners, permissions, secrets, OIDC, branch protection, check wiring, or CI-only infra. Pipeline blockers: record one line in the status and keep remediating everything else.
4. **Ownership before edit.** Load [references/ownership-boundary.md](references/ownership-boundary.md). Edit only codebase-owned defects.
5. **Concurrent by default.** Independent failure clusters (CI jobs, review clusters, scanner clusters) are triaged/fixed in parallel (parallel agents/Tasks). Merge into one worktree batch → one commit.
6. **One commit, one push per cycle.** Zero if nothing codebase-safe remains.
7. **Local verify blocks push.** Run every locally reproducible required gate; fix until green (≤5 re-diag iterations). Remote CI confirms; it does not discover.
8. **Short poll.** After push: poll every **15s** (or `gh run watch`); max **8 minutes** per cycle. Do not idle.
9. **Validate suggestions against current code.** Comment snippets are not ground truth.
10. **No gate weakening / suppressions.** No `NOSONAR`, blanket noqa/type-ignore/eslint-disable, CodeQL dismissals/exclusions, skipped tests, or lowered thresholds. Narrow documented suppression only for a *proven* false positive where a code fix is less safe.
11. **Every thread answered.** Reply Fixed / Deferred / Acknowledged / Disagreed. Resolve when done; leave true human-decision threads open with the decision named.
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
1. **Discover gates (read-only).** Parse workflows + package/Make scripts into a local verify list. Do not edit CI surfaces.
2. **Ingest all signals in parallel.**
   - CI failed logs + annotations
   - Unresolved reviews + inline comments
   - Sonar when configured or check failing → [references/sonarcloud-remediation.md](references/sonarcloud-remediation.md) + `scripts/sonar_fetch.py`
   - CodeQL when check failing or alerts open → [references/codeql-remediation.md](references/codeql-remediation.md) + `scripts/codeql_fetch.py`
   - Debt when toolchain/baseline red → [references/debt-remediation.md](references/debt-remediation.md) + `scripts/debt_audit.py`
   - Details: [references/signal-ingestion.md](references/signal-ingestion.md)
3. **Classify once.** Ownership (`CODEBASE` / `CI_PIPELINE` / `HUMAN` / `FALSE_POSITIVE`) then severity. Cluster by root cause. [references/finding-classifier.md](references/finding-classifier.md) + [references/ownership-boundary.md](references/ownership-boundary.md)
4. **Fix the full safe batch concurrently.** All codebase clusters this cycle. Skip only true human-product forks and CI-pipeline surfaces (note them). Methodology: [references/fix-engine.md](references/fix-engine.md) (**Lesson Recall** before inventing a patch) + scanner refs. Do not commit yet.
5. **Local verify (blocking).** Every local gate green. On fail: fix and re-run all. ≤5 iterations.
6. **Commit + push once.** Conventional message; trailer `Remediation-Cycle: {repo}#{pr}/cycle-{N}`.
7. **Reply.** Canonical replies; resolve completed threads. [references/review-replies.md](references/review-replies.md)
8. **Short-poll + decide.** [references/convergence-loop.md](references/convergence-loop.md). If green and no new actionable signals → merge that PR, then the next older-to-newer open PR. If new codebase work and cycles < 3 → next cycle. If only CI-pipeline / human blockers remain → stop early (more cycles cannot help; do not merge that PR).
9. **Merge.** For each PR that is green + mergeable, with no unanswered codebase review threads:

```bash
gh pr merge {n} --repo {owner}/{repo} --squash --delete-branch
```

Never `--admin`. Never unpack diffs. Oldest `createdAt` first.

## Done When (Converge)

On the final observed head SHA of each open PR, then after merge:

- required checks success (or only recorded CI-pipeline blockers remain — those PRs stay unmerged)
- no merge conflict; review not requesting changes from unaddressed codebase items
- no unanswered actionable review threads
- Sonar/CodeQL/debt: confirmed codebase root causes fixed; remote scanner closure claimed only when observed
- green mergeable PRs are **merged**
- worktree clean
- status names remaining CI-pipeline and human blockers (if any)

## Resource Map

### Diagnose
- [references/diagnose-workflow.md](references/diagnose-workflow.md)
- [references/review-angles.md](references/review-angles.md)
- [references/merge-advise.md](references/merge-advise.md)

### Converge
- [references/ownership-boundary.md](references/ownership-boundary.md) — codebase vs CI vs human
- [references/signal-ingestion.md](references/signal-ingestion.md)
- [references/finding-classifier.md](references/finding-classifier.md)
- [references/fix-engine.md](references/fix-engine.md) — includes lesson recall against `learning/failures/repeated-mistakes.md` + `learning/patterns/quick-fixes.md`
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
max_cycles: 3
max_local_verify_iterations: 5
poll_interval_seconds: 15
max_wait_per_cycle_minutes: 8
parallel_clusters: true
ci_pipeline_policy: note_and_skip  # never edit; no issue-file packaging
```

## Failure Handling

### Diagnose
- PR number missing → STOP; ask or list open PRs
- Skip review comments → BLOCK verdict; fetch comments first
- CI logs unavailable → note `Unknown` for CI; still report reviews/blockers

### Converge
- CI logs missing → retry annotations/job logs once; if ownership unknown, note and continue other clusters
- Rate limit → honor reset, retry once, continue
- Fix breaks a gate → revert that fix, defer with reason, keep the rest of the batch
- Local green / remote red → classify ownership; codebase → next cycle; pipeline → note and stop cycling on that item
- Scanner identity/pagination blocked → stop that scanner cluster; continue others
- Max cycles → report remaining items; do not start cycle 4

## Final Status (required)

### Diagnose
Verdict · blockers · warnings · key review concerns · YNP

### Converge
Cycles run · head SHA · CI result · fixed clusters · PRs merged · remaining open PRs · remaining codebase / CI-pipeline / human blockers · scanner pending-remote if any.
