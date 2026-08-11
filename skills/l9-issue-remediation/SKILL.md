---
name: l9-issue-remediation
description: diagnose or converge open github issues across all non-archived quantum-l9 repos — inventory and rank blockers, fix at the obvious owning repo, hand prs to l9-pr-remediation, and leave graphiti pickup plus issue comment plus conditional root session-reference markdown so the next agent can resume. use when reviewing org issue readiness or blockers, or when the user asks to fix, remediate, unblock, or converge open issues across repos.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, issues, github, diagnose, remediation, cross-repo, unblock, graphiti, fleet]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-11
disable-model-invocation: true
---

# Issue Remediation

## Purpose

Sibling to `l9-pr-remediation` for **GitHub Issues** across the Quantum-L9 fleet.
One pack, two intents: **Diagnose** (read-only inventory/rank) or **Converge**
(mutate to unblock). No packaging theater. Converge stays one sticky issue-cluster
deep, max cycles.

| Intent | Mutates | Triggers | Behavior |
|--------|---------|----------|----------|
| **Diagnose** | no | review / readiness / blockers / `/issues` / “what’s blocking?” | Fleet discover + issue ingest; slim verdict; YNP; **never** commit/push/close |
| **Converge** | yes | fix / remediate / unblock / babysit / autonomy packet | Hot path below; **never** merges PRs (hand to `l9-pr-remediation`) |

### Intent precedence (hard)

1. Mutate language (`fix`, `remediate`, `unblock`, `babysit`, `push`, autonomy packet) → **Converge**.
2. Else readiness / blockers / `/issues` → **Diagnose** only.
3. Ambiguous → **Diagnose**; ask once before Converge.

## Fleet law

Default fleet = **all non-archived `Quantum-L9/*` repositories** discovered via `gh`
(`scripts/fleet_discover.py`). Not `ops/graphiti/group_registry.yaml`.

User may narrow to `{owner}/{repo}` or `{owner}/{repo}#{n}` for a single sticky target.

## Target

Resolve an **issue-cluster**: one primary `{owner}/{repo}#{issue}` plus linked
cross-repo issues that share the same root cause. Default Converge batch = **1
sticky cluster** per invocation. Stay until diagnosed, converged, or blocked.

## Breadcrumb law (Converge closeout — mandatory)

Before claiming Converge done:

1. **Graphiti PICKUP** — required. Fail closed as `BLOCKED_PICKUP` if write fails.
2. **Issue comment** — required on every issue in the sticky cluster (canonical
   template in [references/unblock-breadcrumb.md](references/unblock-breadcrumb.md)).
3. **Root session-reference markdown** (`TODO.md`) — update **only if the file
   already exists** in that repo. Never create it.

## Diagnose

Load [references/diagnose-workflow.md](references/diagnose-workflow.md).

**Forbidden in Diagnose:** commit, push, close/reopen issues, edit worktrees for
fixes, alignment %, gap matrix, deep-eval theater.

## Converge — Inputs → Actions

| Signal | Source | Action |
|--------|--------|--------|
| Open issues | `fleet_discover` + `issue_ingest` | Rank blockers; pick sticky cluster |
| Cross-repo links | body refs, titles, labels | Route owner via [cross-repo-routing.md](references/cross-repo-routing.md) |
| Codebase defects | owning repo source/tests | Fix at obvious owner; local verify; one commit |
| Needs PR green | opened/updated PR | Hand off to **`l9-pr-remediation`** |
| Human/external | product/secrets/third-party | Note; breadcrumb; do not fake close |

## Converge — Outputs (per cycle that changes code)

- One commit, one push (owning repo only)
- Canonical issue comments when cluster state changes
- Short convergence status (what fixed, what remains, breadcrumb state)

No tarballs, run-report schemas, or issue-file bundles.

## Authority Order

1. Latest user instruction and explicit repo/issue scope
2. Current repository source and tests in the owning repo
3. GitHub Issues / search evidence
4. Cross-repo routing evidence (imports, package ownership, issue links)
5. This skill + references
6. Unknown — do not invent; note and continue independent work

## Laws (Converge)

1. **One sticky cluster.** Default max 1 issue-cluster per invocation.
2. **Max three cycles** on that cluster. Never start cycle 4.
3. **Codebase only** in owning repo(s). Never edit `.github/workflows/**`, branch
   protection, org secrets policy, or CI-only infra. Note and skip.
4. **Ownership before edit.** Load [ownership-boundary.md](references/ownership-boundary.md).
5. **Obvious owner.** Shared package/SSOT before ad-hoc consumer edits.
6. **One commit, one push per cycle** in the mutated owning repo. Zero if nothing safe.
7. **Local verify blocks push.** ≤5 re-diag iterations.
8. **No gate weakening / suppressions** as “fixes.”
9. **Never** force-push, merge PRs, expose secrets, or mass-close HUMAN issues.
10. **PR path** → [handoff-to-pr-remediation.md](references/handoff-to-pr-remediation.md).
11. **Breadcrumb law** is part of Done When — PICKUP failure blocks “converged.”
12. **Do not invent** root session-reference markdown files.

## Hot Path (Converge)

0. **Resolve cluster + resume.** Fleet or explicit target. Reuse cycle markers in
   issue comments (`<!-- l9-issue-remediation:... -->`).
1. **Discover gates (read-only)** in the owning repo.
2. **Ingest** issues via scripts; classify ownership + severity; cluster.
3. **Fix** the full safe codebase batch for this cluster (concurrent when independent).
4. **Local verify** → one commit/push with trailer
   `Issue-Remediation-Cycle: {owner}/{repo}#{n}/cycle-{N}`.
5. **PR handoff** when a PR must go green.
6. **Breadcrumbs** — PICKUP + issue comments + conditional session-ref.
7. **Re-ingest + decide** — [convergence-loop.md](references/convergence-loop.md).

## Done When (Converge)

- Codebase root causes for the sticky cluster fixed **or** only HUMAN/EXTERNAL remain
- Linked issues commented; PICKUP written (or status `BLOCKED_PICKUP`)
- Session-ref updated only where `TODO.md` pre-existed
- Worktree clean in mutated repos
- Status names remaining HUMAN / EXTERNAL / CI_PIPELINE / CROSS_REPO blockers

## Resource Map

### Diagnose
- [references/diagnose-workflow.md](references/diagnose-workflow.md)
- [scripts/fleet_discover.py](scripts/fleet_discover.py)
- [scripts/issue_ingest.py](scripts/issue_ingest.py)

### Converge
- [references/ownership-boundary.md](references/ownership-boundary.md)
- [references/finding-classifier.md](references/finding-classifier.md)
- [references/cross-repo-routing.md](references/cross-repo-routing.md)
- [references/fix-engine.md](references/fix-engine.md)
- [references/convergence-loop.md](references/convergence-loop.md)
- [references/handoff-to-pr-remediation.md](references/handoff-to-pr-remediation.md)
- [references/unblock-breadcrumb.md](references/unblock-breadcrumb.md)
- [references/validation-checklist.md](references/validation-checklist.md)
- [scripts/post_issue_comment.py](scripts/post_issue_comment.py)

## Defaults

```yaml
org: Quantum-L9
fleet: non_archived_via_gh
max_clusters_per_invoke: 1
max_cycles: 3
max_local_verify_iterations: 5
breadcrumb:
  graphiti_pickup: required
  issue_comment: required
  session_ref_todo_md: only_if_exists
pr_policy: handoff_to_l9-pr-remediation  # never merge here
```

## Failure Handling

### Diagnose
- `gh` auth / org list fails → STOP; report BLOCKED
- Zero open issues → verdict CLEAN; YNP idle
- Rate limit → honor reset, retry once, else partial inventory with note

### Converge
- Unknown owning repo → do not mutate; ask or Diagnose escalate
- Graphiti PICKUP fails → `BLOCKED_PICKUP`; still post issue comments; do not claim converged
- Fix breaks local gate → revert that fix, defer with reason
- Max cycles → report remaining; do not start cycle 4

## Final Status (required)

### Diagnose
Verdict · top blockers · cross-repo clusters · warnings · YNP

### Converge
Cycles run · owning repo(s) · commits/PRs · fixed clusters · remaining blockers · breadcrumb state (PICKUP / comments / session-ref)
