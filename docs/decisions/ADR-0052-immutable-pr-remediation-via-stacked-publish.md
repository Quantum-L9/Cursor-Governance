# ADR-0052: Immutable PR Remediation via Stacked Publish and Universal Gate Enforcement

## Status

Accepted

## Date

2026-10-04

## Context

In multi-agent collaborative workflows governed by Quantum-L9, multiple pull requests are frequently open concurrently against `main`. When pull requests fail CI, encounter review feedback, or fall behind upstream changes, agents running remediation workflows currently apply in-place mutations directly to the open PR branches.

Historically, amendment `L9_PR_REMEDIATE_SPEED_V1` and CANONICAL_LAW §6.2.8 carved out an exception for `l9-pr-remediation`: while first publications required the full `PR_REMEDIATE=0 make pr` ceremony, subsequent remediation pushes were allowed to run `L9_REMEDIATOR=1 PR_STACK= PR_BASE=origin/main make precommit-repo` followed by a raw `git push` directly to the open PR branch on the rationale that "pytest and conformance stay on CI."

In practice, this architecture produces severe operational pathologies:

1. **The \(O(N^2)\) Merge Cascade under Strict Rulesets:**
   Repositories enforce `strict_required_status_checks_policy: true` on `main` (e.g. repository ruleset `20855699` / `main-protection`). Under this policy, GitHub disallows merging any branch that is not strictly up to date with the HEAD of `main`. When \(N\) sibling PRs are open against `main`, every merge of one PR instantly marks all remaining \(N-1\) PRs as `BEHIND`. Each PR must then merge `main` and rerun all required status checks in a sequential cascade.
2. **Bypassing Publication Gates & Overlap Detection:**
   Allowing raw `git push` during remediation bypasses the governed publication gate in `open_pr_after_gate.sh`, which executes `pr_overlap_check.py`, locked ruff, security checks, and local test suites. As a consequence, unvalidated fixes and non-generated file collisions (such as the collision between PR #681 and PR #682 on `agent_registry.yaml`) are pushed directly to remote branches, triggering failing CI runs and requiring further in-place remediation turns.
3. **In-Flight CI Invalidation and Stack Instability:**
   Pushing new commits to an existing PR branch immediately cancels running CI checks on GitHub and invalidates downstream stacked PRs that branched from the prior HEAD. Multiple agents modifying open branches in-place create race conditions, merge conflicts, and endless "update branch -> rerun CI -> conflict -> edit in place -> push" loops.

## Options Considered

### Option A: Retain in-place mutation with automated `gh pr update-branch` loops
Continue permitting direct `git push` to open PR branches, relying on automated loop scripts to update branches from `main` and poll CI until green.
*Rejected:* This exacerbates the \(O(N^2)\) CI queue storm, wastes hundreds of CI runner minutes, and fails to prevent non-generated file overlaps from reaching GitHub.

### Option B: Require `make pr` on the existing branch without stacking
Disallow raw `git push`, requiring `make pr` for every remediation turn, but continuing to push additional commits directly to the existing PR branch.
*Rejected:* While this ensures local gate passage, it does not resolve in-flight CI cancellation, stack parent invalidation, or the branch-update cascades of sibling PRs.

### Option C: Strict PR Immutability with Stacked Remediation via `make pr`
Enforce that once a pull request exists, its branch is immutable to direct terminal pushes. Any remediation, follow-up, or conflict resolution must be published as a **new stacked PR** via the sanctioned `make pr` publish path (`PR_STACK=auto make pr`), or supersede the prior PR.
*Selected:* Eliminates direct bare pushes across all surfaces, enforces full local verification on every remediation unit, and maintains linear stack ancestry.

## Decision

We establish the architectural rule of **PR Remediation Scope Invariance**:

1. **In-Scope Surgical Fixes (Within-Boundary Remediation):**
   When replying to review threads, fixing tests, or applying surgical corrections to files that were already created or modified by the original pull request (`file in pr.files`), the commit is pushed directly to the open PR branch being remediated (after local verify `make precommit-repo`). This avoids unnecessary PR sprawl for small, in-scope fixes while preserving the PR's claimed file boundary in the fleet.
2. **Scope-Expanding Fixes (New Files Require a New Stacked PR):**
   If remediation requires modifying, adding, or deleting any file *outside* the original PR's file footprint (`new_files = changed_files - pr.files`), pushing directly to the open PR branch is **strictly forbidden**. Any scope expansion must be published as a **new stacked PR** via `PR_STACK=auto PR_REMEDIATE=0 make pr` to prevent uncoordinated collisions with newer open PRs and downstream stack branches.

### 1. Scope-Enforcing Publication Gate (`first_publication_gate.py`)
`first_publication_gate.py` enforces the scope boundary mechanically:
- Pushes to branches with no open PR are denied as first publications (must use `make pr`).
- Pushes to open PR branches that touch only files already in the PR diff are allowed as in-scope remediation.
- Pushes to open PR branches that touch new files outside the PR diff are denied as scope expansions, requiring publication of a new stacked PR via `PR_STACK=auto make pr`.

### 2. Linear Merge Trains Over Sibling Fan-Out
To prevent the \(O(N^2)\) update cascade caused by `strict_required_status_checks_policy: true`, concurrent workstreams stack linearly:
$$\text{main} \leftarrow \text{PR}_1 \leftarrow \text{PR}_2 \leftarrow \dots \leftarrow \text{PR}_N$$
Because each child branch already incorporates the commits of its parent, merging $\text{PR}_1$ into `main` using ancestry-preserving `--merge` leaves $\text{PR}_2$ immediately mergeable without requiring a full re-merge of `main` or an out-of-date branch invalidation cycle.

## Consequences

1. **Gate Parity:** Every remediation unit undergoes the identical gate as initial code (format, lint, pre-commit, security scans, test suite, and overlap checking) before reaching remote infrastructure.
2. **Immutability of In-Flight PRs:** Existing PR branches remain stable; CI runs are never aborted mid-flight by unexpected terminal pushes.
3. **No Bare Pushes:** Agents cannot bypass publication checks using `git push`. The publication plane becomes fully deterministic.
4. **Skill Realignment:** `skills/l9-pr-remediation` and its reference manuals are updated to remove the bare-push instructions and mandate stacked child PR creation via `make pr`.
5. **Rule Alignment:** `rules/48-make-pr-remediation.mdc`, `CANONICAL_LAW.md`, and `AGENTS.md` are amended append-only to reflect universal `make pr` publication.

## References

- [1] `CANONICAL_LAW.md` §6.2.8 (First publication plane)
- [2] `AGENTS.md` `L9_PR_REMEDIATE_SPEED_V1` (Historical speed carve-out, superseded)
- [3] `rules/48-make-pr-remediation.mdc` (PR publication and remediation rule)
- [4] `rules/53-pr-overlap-guardrail.mdc` (PR overlap and stacking guardrails)
- [5] `ops/autonomy/first_publication_gate.py` (Publication plane enforcement)
- [6] GitHub Ruleset `20855699` (`main-protection`: `strict_required_status_checks_policy: true`)
