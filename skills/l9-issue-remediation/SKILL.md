---
name: l9-issue-remediation
description: remediator for open github issues across all non-archived quantum-l9 repos — verify each issue is real before trusting it, drain clusters until a human architecture blocker, ask a recommended multiple-choice (A first), then resume. close phantoms; land real fixes on a matching or stacked pr. use when the user runs /issues or /l9-issue-remediation, or asks to fix, remediate, unblock, or converge open issues.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, issues, github, diagnose, remediation, cross-repo, unblock, graphiti, fleet]
  owner: igor_beylin
  status: active
  version: 1.3.0
  updated: 2026-08-30
---

# Issue Remediation

## Purpose

Sibling to `l9-pr-remediation` for **GitHub Issues** across the Quantum-L9 fleet.
Two intents: **Diagnose** (auditor) or **Converge** (remediator). No packaging
theater. Converge runs at **max autonomy**: verify every issue, drain all
automatable clusters, do not stop between them. Stop only when a human
(architecture / product / external) is required — then ask a recommended
multiple-choice (**A** first) and resume.

| Intent | Mutates | Triggers | Behavior |
|--------|---------|----------|----------|
| **Diagnose** | already-resolved close only | `/issues diagnose` / readiness / “what’s blocking?” | Fleet ingest + rank; **close already-fixed in the same turn**; **never** commit/push/fix; **never** chain `/l9-pr-remediation` |
| **Converge** | yes | `/issues` / `/l9-issue-remediation` / fix / remediate / unblock / babysit | Hot path; land on PRs; **close in the same turn when fixed**; chain remediator **only if** `open_issues=0`; **never** `gh pr merge` |

### Intent precedence (hard)

1. `/issues`, `/l9-issue-remediation`, or mutate language (`fix`, `remediate`,
   `unblock`, `babysit`, `push`, autonomy packet) → **Converge**.
2. `diagnose` / readiness / “what’s blocking?” → **Diagnose** only.
3. Ambiguous bare “issues” → **Converge**.

## Fleet law

Default fleet = **all non-archived `Quantum-L9/*` repositories** discovered via `gh`
(`scripts/fleet_discover.py`). Not `ops/graphiti/group_registry.yaml`.

User may narrow to `{owner}/{repo}` or `{owner}/{repo}#{n}`.

## Target

Resolve **issue-clusters**: one primary `{owner}/{repo}#{issue}` plus linked
cross-repo issues that share the same root cause. Default Converge batch =
**all** automatable clusters (`max_clusters_per_invoke: all`), ranked by
`scripts/cluster_rank.py`.

## Breadcrumb law (Converge closeout — mandatory)

Before claiming Converge done:

1. **Graphiti PICKUP** — required. Fail closed as `BLOCKED_PICKUP` if write fails.
2. **Issue comment** — required on every issue in each touched cluster
   ([references/unblock-breadcrumb.md](references/unblock-breadcrumb.md)).
3. **Close-now law** — if the issue is `already-fixed` / `not-reproducible` /
   `does-not-exist` / `duplicate` / `superseded`, or the fix is on a PR
   (`status=fixed`), **close it in this turn** via
   `scripts/close_resolved_issue.py` (or `gh issue close` if the comment
   helper is blocked). Do not report the verdict and leave the issue OPEN.
   Do not defer close to merge, to the next cluster, or to a later session.
   An OPEN GitHub row after a resolved verdict is a skill failure.
4. **Root session-reference markdown** (`TODO.md`) — update **only if the file
   already exists** in that repo. Never create it.

## Diagnose

Load [references/diagnose-workflow.md](references/diagnose-workflow.md).

**Forbidden in Diagnose:** commit, push, fix worktrees, chain
`/l9-pr-remediation`, alignment %, gap matrix, deep-eval theater.

**Allowed in Diagnose:** already-resolved close with evidence — **required
in the same turn**, not optional hygiene. A stale backup copy of this skill
that says “Diagnose never close” is not authority.

## Converge — Inputs → Actions

| Signal | Source | Action |
|--------|--------|--------|
| Open issues | `fleet_discover` + `issue_ingest` + `cluster_rank` | Rank; drain automatable queue |
| Cross-repo links | body refs, titles, labels | Route owner via [cross-repo-routing.md](references/cross-repo-routing.md) |
| Codebase defects | owning repo source/tests | Fix at obvious owner; local verify; land on PR |
| Fix belongs on open PR | [pr-landing.md](references/pr-landing.md) | Push that branch |
| Else | newest open PR | `PR_REMEDIATE=0 make pr` stacked (`PR_STACK=auto`) |
| `open_issues == 0` | `open_issues_gate.py --intent converge` | Chain **`l9-pr-remediation`** |
| `open_issues > 0` | leftover OPEN including HUMAN/EXTERNAL | `BLOCKED_OPEN_ISSUES` — do not chain |
| Human/external / architecture | product/secrets/SSOT move | Drain other clusters; then [human-blocker-mcq.md](references/human-blocker-mcq.md) (**A** = recommended); resume after the letter |
| Phantom / stale / already-fixed issue | [issue-verify.md](references/issue-verify.md) | Close in this turn with evidence; do not remediate; do not leave OPEN |

## Converge — Outputs (per cycle that changes code)

- One commit, landed on the matching open PR or a new stacked PR
- Canonical issue comments + close when `status=fixed`
- Short convergence status (what fixed, `open_issues`, breadcrumb state)

No tarballs, run-report schemas, or issue-file bundles.

## Authority Order

1. Latest user instruction and explicit repo/issue scope
2. Current repository source and tests in the owning repo
3. GitHub Issues / search evidence
4. Cross-repo routing evidence (imports, package ownership, issue links)
5. This skill + references
6. Unknown — do not invent; note and continue independent work

## Laws (Converge)

1. **Max autonomy.** Default `max_clusters_per_invoke: all`, highest
   leverage first. Do not stop between issues. Per-cluster max 3 cycles.
   Never start cycle 4 on one cluster. Stop the invoke only when the next
   step is impossible without a human — then
   [human-blocker-mcq.md](references/human-blocker-mcq.md) and resume.
2. **Verify before trust.** Recreate the live GitHub issue and prove the
   defect in the owning repo ([issue-verify.md](references/issue-verify.md))
   before any patch. Close if it does not exist or is not reproducible;
   remediate only if it does. Agents invent issues — do not assume OPEN
   means correct. A verified `already-fixed` issue is closed **before**
   the next tool call that starts another cluster.
3. **Codebase only** in owning repo(s). Never edit `.github/workflows/**`,
   branch protection, org secrets policy, or CI-only infra. Note and skip.
4. **Ownership before edit.** Load [ownership-boundary.md](references/ownership-boundary.md).
5. **Obvious owner.** Shared package/SSOT before ad-hoc consumer edits.
6. **One commit per cycle** in the mutated owning repo. Zero if nothing safe.
7. **PR landing.** Matching open PR wins; else stacked PR on newest; else
   first PR on `origin/main`. See [pr-landing.md](references/pr-landing.md).
8. **Local verify blocks publish.** ≤5 re-diag iterations.
9. **No gate weakening / suppressions** as “fixes.”
10. **Never** force-push, merge PRs, expose secrets, or mass-close HUMAN
    issues. Evidence-close only as
    superseded|duplicate|already-fixed|not-reproducible|does-not-exist.
11. **`/l9-pr-remediation` only after `open_issues=0`.**
    [handoff-to-pr-remediation.md](references/handoff-to-pr-remediation.md).
12. **Breadcrumb law** is part of Done When — PICKUP failure or a resolved
    issue still OPEN blocks “converged.” Close-now is not optional commentary.
13. **Do not invent** root session-reference markdown files.
14. **Architecture stays human.** Recommend the optimal path as **A**; do not
    implement a new architecture until they pick a letter.

## Hot Path (Converge)

0. **Bind target + resume.** Fleet or explicit repo. Reuse cycle markers
   (`<!-- l9-issue-remediation:... -->`).
1. **Discover gates (read-only)** in the owning repo.
2. **Ingest + rank** — `issue_ingest.py` then `cluster_rank.py`.
3. **Verify** each issue in the current cluster
   ([issue-verify.md](references/issue-verify.md)). Close phantoms; skip
   404/already-CLOSED. Do not patch until `exists`.
4. **Fix** only `exists` items (concurrent when independent).
   [fix-engine.md](references/fix-engine.md) (**Lesson Recall**).
5. **Local verify** → commit with trailer
   `Issue-Remediation-Cycle: {owner}/{repo}#{n}/cycle-{N}`.
6. **Land on PR** — [pr-landing.md](references/pr-landing.md).
7. **Breadcrumbs** — PICKUP + comments + **close if fixed** + conditional session-ref.
8. **Re-ingest + gate** — [convergence-loop.md](references/convergence-loop.md).
   Next automatable cluster immediately. HUMAN/ARCHITECTURE leftover →
   [human-blocker-mcq.md](references/human-blocker-mcq.md), then resume.
   Chain `/l9-pr-remediation` **only** when `open_issues_gate.py` says `chain: true`.

## Done When (Converge)

- Automatable clusters drained (verified, closed, or fixed)
- Remaining HUMAN / ARCHITECTURE / EXTERNAL presented as recommended-A
  questions; queue resumes after letters
- Every resolved issue (`status=fixed` / already-fixed / phantom) is
  CLOSED on GitHub in the same turn — not “will close after merge”
- Linked issues commented; PICKUP written (or status `BLOCKED_PICKUP`)
- Session-ref updated only where `TODO.md` pre-existed
- Worktree clean in mutated repos
- `/l9-pr-remediation` invoked **only if** bound-target `open_issues=0`;
  otherwise status `BLOCKED_OPEN_ISSUES` (after the MCQ turn if humans remain)

## Resource Map

### Diagnose
- [references/diagnose-workflow.md](references/diagnose-workflow.md)
- [scripts/fleet_discover.py](scripts/fleet_discover.py)
- [scripts/issue_ingest.py](scripts/issue_ingest.py)
- [scripts/cluster_rank.py](scripts/cluster_rank.py)
- [scripts/close_resolved_issue.py](scripts/close_resolved_issue.py)
- [scripts/open_issues_gate.py](scripts/open_issues_gate.py)
- [references/issue-verify.md](references/issue-verify.md)

### Converge
- [references/issue-verify.md](references/issue-verify.md)
- [references/human-blocker-mcq.md](references/human-blocker-mcq.md)
- [references/ownership-boundary.md](references/ownership-boundary.md)
- [references/finding-classifier.md](references/finding-classifier.md)
- [references/cross-repo-routing.md](references/cross-repo-routing.md)
- [references/fix-engine.md](references/fix-engine.md)
- [references/pr-landing.md](references/pr-landing.md)
- [references/convergence-loop.md](references/convergence-loop.md)
- [references/handoff-to-pr-remediation.md](references/handoff-to-pr-remediation.md)
- [references/unblock-breadcrumb.md](references/unblock-breadcrumb.md)
- [references/validation-checklist.md](references/validation-checklist.md)
- [scripts/post_issue_comment.py](scripts/post_issue_comment.py)
- [scripts/close_resolved_issue.py](scripts/close_resolved_issue.py)
- [scripts/cluster_rank.py](scripts/cluster_rank.py)
- [scripts/pr_landing.py](scripts/pr_landing.py)
- [scripts/open_issues_gate.py](scripts/open_issues_gate.py)
- [scripts/self_test.py](scripts/self_test.py)

## Defaults

```yaml
org: Quantum-L9
fleet: non_archived_via_gh
max_clusters_per_invoke: all
max_autonomy: until_human_blocker
recommend_letter: A
verify_before_trust: true
max_cycles: 3
max_local_verify_iterations: 5
make_pr: true
chain_pr_remediation: after_open_issues_zero
close_resolved: true
close_now_same_turn: true
breadcrumb:
  graphiti_pickup: required
  issue_comment: required
  close_if_fixed: required
  close_now_same_turn: required
  session_ref_todo_md: only_if_exists
pr_policy: land_then_chain_after_open_issues_zero  # never merge here
```

## Failure Handling

### Diagnose
- `gh` auth / org list fails → STOP; report BLOCKED
- Zero open issues → verdict CLEAN; YNP idle
- Rate limit → honor reset, retry once, else partial inventory with note

### Converge
- Unknown owning repo → do not mutate; ask or Diagnose escalate
- Graphiti PICKUP fails → `BLOCKED_PICKUP`; still post comments; do not claim converged
- `status=fixed` still OPEN → not converged; run `close_resolved_issue.py`
- `open_issues != 0` after automatable drain → present
  [human-blocker-mcq.md](references/human-blocker-mcq.md); status
  `BLOCKED_OPEN_ISSUES` until letters land or hold; do not chain
  `/l9-pr-remediation` while any issue stays OPEN
- Fix breaks local gate → revert that fix, defer with reason
- Max cycles on a cluster → continue other clusters; do not start cycle 4 on that one

## Final Status (required)

### Diagnose
Verdict · top blockers · cross-repo clusters · already-closed · warnings · YNP

### Converge
Cycles run · owning repo(s) · commits/PRs · fixed clusters · `open_issues` ·
chain (`CHAIN_PR_REMEDIATION` / `BLOCKED_OPEN_ISSUES`) · breadcrumb state
