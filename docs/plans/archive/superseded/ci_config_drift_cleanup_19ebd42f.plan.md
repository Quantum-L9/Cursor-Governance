---
name: CI Config Drift Cleanup
overview: "Evidence-backed plan (Standard mode) to close 3 confirmed drift findings from the pyproject.toml / conftest.py / CI workflow audit: unpinned semgrep in l9-analysis.yml, dangling baseline-ratchet.yml references in 3 files, and stale security.yml documentation in AGENTS.md. Doc/config-only, zero behavior change, git-reversible."
todos:
  - id: PI-01-fix-l9-analysis-yml
    content: "l9-analysis.yml: pin semgrep==1.164.0 (line 89) + remove dangling baseline-ratchet.yml reference from L9_CORE_REF comment (lines 25-27)"
    status: pending
  - id: PI-02-fix-governance-readme
    content: "governance/README.md: remove dangling baseline-ratchet.yml reference (lines 36-40)"
    status: pending
  - id: PI-03-fix-agents-md
    content: "AGENTS.md: remove baseline-ratchet.yml row (line 292), rewrite security.yml row as tombstone (line 293), remove dependency-scan/trivy-scan advisory rows (~lines 320-321)"
    status: pending
  - id: PI-04-verify
    content: "Run verification grep sweep (baseline-ratchet, semgrep pin, dependency-scan/trivy-scan) and confirm AGENTS.md workflow table row count = 9"
    status: pending
isProject: false
---

# CI Config Drift Cleanup

## Plan Status: Ready — Planning Mode: Standard

Bounded, low-risk, doc/config-only correction with a small affected surface (3 files) and straightforward validation (grep + row-count check). Standard mode applies rather than Quick because the plan formalizes a findings register, decision log, and full validation/rollback matrix; Deep/Release modes do not apply — no architecture, security, migration, or lifecycle (commit/push) work is in scope.

## Target Binding

- **Repo root:** `/Users/macm2/Library/CloudStorage/Dropbox/Repo_Dropbox_IB/IB-Odoo_19-1`
- **Modification targets (verified by direct read in prior audit turn):**
  - [.github/workflows/l9-analysis.yml](.github/workflows/l9-analysis.yml)
  - [.github/governance/README.md](.github/governance/README.md)
  - [AGENTS.md](AGENTS.md)
- **Explicitly not modified:** `pyproject.toml`, `tests/conftest.py` — both audited clean; no drift found in either.
- **Revision:** current working tree at time of audit; no branch/commit pin required since edits are local and unpushed.

## Objective & Desired Outcomes

**Objective:** Eliminate every confirmed documentation/config inconsistency surfaced by the audit so that CI workflow files and `AGENTS.md` accurately describe what runs today, with zero change to gating behavior.

**Desired outcomes (all Required):**
- `l9-analysis.yml` installs the same pinned semgrep version (`1.164.0`) as `Makefile` and `ci.yml`.
- No file in the repo references `baseline-ratchet.yml` as if it still exists.
- `AGENTS.md` describes `security.yml` as the disabled tombstone it actually is, and lists no advisory jobs (`dependency-scan`, `trivy-scan`) that no longer exist.
- `AGENTS.md`'s workflow table row count reconciles with its own "9 Workflow Files" header.

**Explicitly excluded (no action):** `pyproject.toml`'s `norecursedirs`/ruff-`exclude`/pyright-`exclude`/coverage-`omit` entries for `addons`, `tests-odoo`, `odoo-enterprise` — confirmed intentional defensive/forward-looking config, not drift.

## Authority & Governing Rules

- [`.cursor/rules/99-no-auto-commit.mdc`](.cursor/rules/99-no-auto-commit.mdc), [`01-git-push-prohibition.mdc`](.cursor/rules/01-git-push-prohibition.mdc), [`96-git-push-approval.mdc`](.cursor/rules/96-git-push-approval.mdc) — commit and push each require a **separate, explicit** user instruction after these edits land. This plan's implementation handoff stops at file edits.
- [`.cursor/rules/60-anti-patterns.mdc`](.cursor/rules/60-anti-patterns.mdc) "Huge, unscoped edits" anti-pattern — satisfied: scope is bounded to exactly the 3 verified findings below, nothing adjacent.
- [`AGENTS.md`](AGENTS.md) "CI Compliance Checklist" — this plan corrects that same document; no conflicting authority.
- No architecture, security, or data-migration policy adapter applies (comment/doc-text and version-pin changes only).

## Current State (Verified)

- `l9-analysis.yml` line 89 installs semgrep unpinned: `pip install --upgrade pip semgrep`. `Makefile:148` and `ci.yml:80` both pin `semgrep==1.164.0`.
- `l9-analysis.yml` lines 25-27 and `.github/governance/README.md` lines 36-40 both reference `.github/workflows/baseline-ratchet.yml` by name as an existing, trusted sibling workflow. That file does not exist at HEAD (confirmed via directory listing — only `ci.yml`, `l9-analysis.yml`, `security.yml`, `changelog.yml`, `repo-index.yml`, `auto-merge.yml`, `auto-review-request.yml`, `release.yml`, `pr-autopilot.yml` = 9 files).
- `AGENTS.md` line 292 lists `baseline-ratchet.yml` in the active-workflow table (phantom row). Line 293 describes `security.yml` as running `pip-audit, Trivy, Gitleaks` on push/PR/weekly. Actual `security.yml` content: single `placeholder` job on `workflow_dispatch` only (tombstone). Lines ~320-321 list `dependency-scan` and `trivy-scan` advisory jobs that reference this tombstoned workflow and no longer exist.

## Findings Register

- **F-01** (Confirmed, Severity Low): Unpinned semgrep in `l9-analysis.yml` — inconsistent with the repo's stated pinning policy; a floating version can silently change lint behavior between CI runs without a diff to review.
- **F-02** (Confirmed, Severity Low): Dangling `baseline-ratchet.yml` references, 3 locations —
  - F-02a: `l9-analysis.yml` lines 25-27 (comment)
  - F-02b: `.github/governance/README.md` lines 36-40 (prose)
  - F-02c: `AGENTS.md` line 292 (table row)
- **F-03** (Confirmed, Severity Low): Stale `security.yml` documentation in `AGENTS.md`, 2 locations —
  - F-03a: line 293 (workflow description row)
  - F-03b: lines ~320-321 (advisory-jobs table rows)

All three findings are documentation-drift only; none indicate a functional CI gap (the real checks — semgrep, secret-scan — already run correctly via `ci.yml`/`l9-analysis.yml`; only the pin and the prose are wrong).

## Assumptions & Decisions

- **Assumption A-01:** No other file in the repo references `baseline-ratchet.yml`, `dependency-scan`, or `trivy-scan` beyond the locations already identified. Confidence: Probable (based on prior grep sweep of `.github/` and `AGENTS.md`; not re-verified against the full repo tree in this pass). Resolved by: PI-04's verification grep, which is repo-root-scoped, not limited to the 3 known files.
- **Decision D-01** (Open, non-blocking, recommended default: No): Whether this 3-file change set warrants a formal GMP evidence report per [`.cursor/rules/83-gmp-contracts.mdc`](.cursor/rules/83-gmp-contracts.mdc) and `AGENTS.md`'s own "quick fix (< 3 files, no GMP) → no report needed" guidance. This change touches exactly 3 files, which is a boundary case. Recommendation: no GMP report — the change is a documentation/comment/version-pin correction with no code, model, or test surface, not "significant work" in the GMP sense. Authority: user. If the user wants a report anyway, add it as a follow-up item; it does not change any plan item's content.

## Recommended Strategy

Direct in-place literal-string edits to the 3 affected files, using the exact before/after text already verified against current file content (no re-derivation needed). Rejected alternatives: none — this is a single-viable-strategy correction (there is no material tradeoff between "fix the stale text" and any alternative; rewriting history or adding new automation to prevent recurrence was considered and rejected as disproportionate leverage for a 3-file doc fix).

## Responsibility Map

- **CI workflow config** (owner: repo CI maintainers) — `l9-analysis.yml`. Depends on: `Makefile`/`ci.yml` as the source-of-truth for the semgrep pin value.
- **Governance docs** (owner: repo governance maintainers) — `.github/governance/README.md`. No downstream consumers beyond human readers.
- **Agent-facing repo docs** (owner: repo maintainers, consumed by all AGENTS.md-compatible tools) — `AGENTS.md`. Source of truth for what workflows exist; must match `.github/workflows/*.yml` on disk.

## Plan Items

### PI-01 — Align l9-analysis.yml with the repo-wide semgrep pin and drop the dead sibling-workflow reference

- **Objective:** `l9-analysis.yml` installs `semgrep==1.164.0` and its `L9_CORE_REF` comment no longer names a nonexistent file.
- **Rationale:** Closes F-01, F-02a.
- **Category:** Configuration | **Priority:** Medium | **Necessity:** Required | **Confidence:** Confirmed
- **Owner boundary:** CI workflow config
- **Affected artifacts:** [.github/workflows/l9-analysis.yml](.github/workflows/l9-analysis.yml) — line 89; lines 25-27
- **Prerequisites:** None
- **Inputs:** Verified current file content (this audit)
- **Actions:**
  1. Line 89 — replace:
     ```yaml
               pip install --upgrade pip semgrep
     ```
     with:
     ```yaml
               pip install --upgrade pip "semgrep==1.164.0"
     ```
  2. Lines 25-27 — replace:
     ```yaml
     env:
       # Keep in lockstep with .github/workflows/baseline-ratchet.yml's core-revision.
       L9_CORE_REF: "d81a06ed821106a487df2e5ad06d93e347392af6"
     ```
     with:
     ```yaml
     env:
       # Pinned Quantum-L9/l9-ci-core commit for this workflow's actions (resolve-governance,
       # provision-sdk, invoke-sdk, validate-bundle, route-artifacts, build-artifact-manifest,
       # publish-analysis). Bump deliberately, not opportunistically.
       L9_CORE_REF: "d81a06ed821106a487df2e5ad06d93e347392af6"
     ```
- **Preserved invariants:** `L9_CORE_REF` value (`d81a06ed821106a487df2e5ad06d93e347392af6`) unchanged; job structure, triggers, and all other steps unchanged.
- **Expected changes:** Semgrep install pinned; stale comment rewritten.
- **Prohibited changes:** No edits to job logic, triggers, permissions, or any other env var in this file.
- **Acceptance criteria:** `grep -n 'semgrep==1.164.0' .github/workflows/l9-analysis.yml` matches; `grep -n 'baseline-ratchet' .github/workflows/l9-analysis.yml` returns zero matches.
- **Validation:** Structural (YAML remains syntactically valid) + the two targeted greps above.
- **Rollback/recovery:** `git checkout -- .github/workflows/l9-analysis.yml` (single-file, no cross-file state).
- **Risk:** Low | **Risk factors:** None material (comment/pin-only). | **Effort:** Trivial | **Uncertainty:** Low | **Parallelization:** Independent
- **Postconditions:** File content matches the two target blocks above exactly.
- **Closes findings:** F-01, F-02a
- **Status:** Ready

### PI-02 — Remove dangling baseline-ratchet.yml reference from governance README

- **Objective:** `.github/governance/README.md` no longer asserts that `baseline-ratchet.yml` exists or that pins must be kept "in lockstep" with it.
- **Rationale:** Closes F-02b.
- **Category:** Documentation | **Priority:** Medium | **Necessity:** Required | **Confidence:** Confirmed
- **Owner boundary:** Governance docs
- **Affected artifacts:** [.github/governance/README.md](.github/governance/README.md) — lines 36-40
- **Prerequisites:** None
- **Inputs:** Verified current file content (this audit)
- **Actions:** Replace:
  ```markdown
  `.github/workflows/l9-analysis.yml` pins `Quantum-L9/l9-ci-core` to
  `d81a06ed821106a487df2e5ad06d93e347392af6` — the same commit
  `.github/workflows/baseline-ratchet.yml` already trusts (GATE-01 adoption).
  Bump both pins together; don't let them drift to different Core revisions.
  ```
  with:
  ```markdown
  `.github/workflows/l9-analysis.yml` pins `Quantum-L9/l9-ci-core` to
  `d81a06ed821106a487df2e5ad06d93e347392af6`. Bump this pin deliberately when
  adopting a new Core revision, not opportunistically.
  ```
- **Preserved invariants:** The commit SHA (`d81a06ed821106a487df2e5ad06d93e347392af6`) and its meaning (pin for `l9-analysis.yml`'s actions) are unchanged; only the reference to the deleted sibling workflow is removed.
- **Expected changes:** Prose no longer implies a second workflow trusts/adopts this pin.
- **Prohibited changes:** No other section of the README is touched.
- **Acceptance criteria:** `grep -n 'baseline-ratchet' .github/governance/README.md` returns zero matches; SHA string still present and unchanged.
- **Validation:** Targeted grep above; visual diff confirms no other line changed.
- **Rollback/recovery:** `git checkout -- .github/governance/README.md`.
- **Risk:** Low | **Risk factors:** None. | **Effort:** Trivial | **Uncertainty:** Low | **Parallelization:** Independent
- **Postconditions:** File content matches target block above exactly.
- **Closes findings:** F-02b
- **Status:** Ready

### PI-03 — Correct AGENTS.md workflow and advisory tables

- **Objective:** `AGENTS.md`'s CI documentation matches what actually exists and runs: 9 workflow rows (no phantom `baseline-ratchet.yml`), `security.yml` described as the tombstone it is, and no advisory rows for jobs that no longer exist.
- **Rationale:** Closes F-02c, F-03a, F-03b.
- **Category:** Documentation | **Priority:** Medium | **Necessity:** Required | **Confidence:** Confirmed
- **Owner boundary:** Agent-facing repo docs
- **Affected artifacts:** [AGENTS.md](AGENTS.md) — line 292; line 293; ~lines 320-321
- **Prerequisites:** None (independent of PI-01/PI-02; no shared file)
- **Inputs:** Verified current file content (this audit); confirmed 9 files on disk in `.github/workflows/`
- **Actions:**
  1. Line 292 — delete the row entirely:
     ```markdown
     | `baseline-ratchet.yml` | push/PR → Staging | GATE-01 pytest baseline ratchet (Quantum-L9/l9-ci-core reusable workflow) — required tests, quarantine ledger, packet-envelope ledger |
     ```
  2. Line 293 — replace:
     ```markdown
     | `security.yml` | push + PR → staging/main + weekly | pip-audit, Trivy, Gitleaks |
     ```
     with:
     ```markdown
     | `security.yml` | manual only (`workflow_dispatch`) | Tombstone — disabled; all checks moved to `ci.yml`'s `secret-scan` job |
     ```
  3. ~Lines 320-321 (advisory/"Non-blocking" table) — delete both rows:
     ```markdown
     | `dependency-scan` | `security.yml` | `pip-audit \|\| true` |
     | `trivy-scan` | `security.yml` | `exit-code: 0` |
     ```
     leaving only the `secret-scan` and `l9-analysis.yml` rows in that table.
- **Preserved invariants:** The "9 Workflow Files" header count is unchanged (it was already correct); every other row in both tables is unchanged.
- **Expected changes:** Active-workflow table drops to exactly 9 data rows; advisory table loses its 2 stale rows.
- **Prohibited changes:** No edits to any other section of `AGENTS.md` (CI Compliance Checklist, module structure, boundaries, etc. are all out of scope).
- **Acceptance criteria:** `grep -n 'baseline-ratchet' AGENTS.md` and `grep -n 'dependency-scan\|trivy-scan' AGENTS.md` both return zero matches; manual count of the active-workflow table body rows equals 9; the `security.yml` row text matches the replacement above.
- **Validation:** Targeted greps above + row-count check against the 9 files listed in Current State.
- **Rollback/recovery:** `git checkout -- AGENTS.md`.
- **Risk:** Low | **Risk factors:** None. | **Effort:** Small (3 edits, 1 file) | **Uncertainty:** Low | **Parallelization:** Independent
- **Postconditions:** Both tables in `AGENTS.md` reconcile with the actual 9 files in `.github/workflows/` and `security.yml`'s actual tombstone content.
- **Closes findings:** F-02c, F-03a, F-03b
- **Status:** Ready

### PI-04 — Verification sweep

- **Objective:** Prove, with reproducible commands, that no dangling reference or version-pin inconsistency remains anywhere in the repo (not just the 3 known files), closing Assumption A-01.
- **Rationale:** Closes the loop on F-01, F-02(a/b/c), F-03(a/b), and validates Assumption A-01 at repo scope.
- **Category:** Validation | **Priority:** Medium | **Necessity:** Required | **Confidence:** Confirmed
- **Owner boundary:** Cross-cutting (spans all 3 edited artifacts)
- **Affected artifacts:** None modified — read-only checks against the whole repo tree.
- **Prerequisites:** PI-01, PI-02, PI-03 complete.
- **Inputs:** Edited file states from PI-01–PI-03.
- **Actions:** Run, repo-root-scoped (not limited to the 3 known files, per A-01):
  - `grep -rn "baseline-ratchet" .` → expect zero results.
  - `grep -n "semgrep" .github/workflows/l9-analysis.yml` → expect `semgrep==1.164.0`.
  - `grep -rn "dependency-scan\|trivy-scan" .` → expect zero results.
  - Manual count of `AGENTS.md`'s active-workflow table body rows → expect 9, matching `ls .github/workflows/*.yml | wc -l`.
- **Preserved invariants:** N/A (read-only).
- **Expected changes:** None — this item produces evidence, not edits.
- **Prohibited changes:** No file edits in this item.
- **Acceptance criteria:** All four checks above pass with their expected output.
- **Validation:** This item is itself the validation step for PI-01–PI-03.
- **Rollback/recovery:** Not applicable — read-only.
- **Risk:** Low | **Risk factors:** None. | **Effort:** Trivial | **Uncertainty:** Low | **Parallelization:** Sequential (after Wave 1)
- **Postconditions:** Repo-wide evidence that F-01 through F-03b are closed and A-01 holds.
- **Closes findings:** Final closure evidence for F-01, F-02a/b/c, F-03a/b
- **Status:** Ready (blocked until Wave 1 completes)

## Execution Waves & Critical Path

- **Wave 1 (parallel, no shared files, no write conflicts):** PI-01, PI-02, PI-03.
- **Wave 2 (sequential, depends on Wave 1):** PI-04.
- **Critical path:** any one Wave-1 item (all are Trivial/Small and equally short) → PI-04. No item dominates; total path length is 2 waves.

## Validation Matrix

- PI-01 → targeted grep (semgrep pin, no baseline-ratchet string) — Mandatory
- PI-02 → targeted grep (no baseline-ratchet string) — Mandatory
- PI-03 → targeted grep (no baseline-ratchet/dependency-scan/trivy-scan strings) + manual row-count reconciliation — Mandatory
- PI-04 → repo-root-scoped re-run of all greps above + row-count check — Mandatory, final/whole-state validation
- Regression protection: none needed — no behavior-changing code path exists in this change set; the only "regression" risk is a future re-introduction of the same drift, which is out of scope to automate per Leverage Analysis below.

## Rollback & Recovery

- Every plan item maps to a single-file `git checkout -- <path>` revert; no item depends on another item's state, so any subset can be reverted independently without touching the others.
- No irreversible steps in this plan. No migration, no runtime state, no deployment.

## Risk Register

- **Overall risk: Low.** No security, data-integrity, compatibility, or availability surface is touched (config comments and Markdown prose only).
- **Risk R-01:** Transcription error introduces a new inaccuracy while fixing an old one. Likelihood: Low. Impact: Low (caught immediately by PI-04's grep sweep before any commit). Mitigation: PI-04 is mandatory before handoff is considered complete. Detection: grep exit codes / manual diff review. Rollback: per-file `git checkout`.

## Leverage Analysis

- **Highest-leverage root-cause repair:** PI-02/PI-03 remove the shared root cause (stale references to a workflow file that was deleted without a corresponding doc sweep) rather than patching each symptom with different wording.
- **Highest-leverage deletion:** Removing the 3 dead `baseline-ratchet.yml` references and the 2 dead advisory rows reduces confusion for the next reader/agent more than any addition would.
- **Highest-leverage validation addition:** PI-04's repo-root-scoped grep sweep (not limited to the 3 known files) — reusable ad hoc as a quick drift check in future audits.
- **Speculative opportunities considered and rejected:** Adding an automated CI check that fails when `AGENTS.md` references a nonexistent workflow file. Rejected for this plan — disproportionate permanent complexity/maintenance cost for a one-time doc correction; no evidence of recurring drift frequency that would justify it. Not included as a plan item; flagged here only as a deferred idea for the user to raise separately if desired.

## Lifecycle Plan: Not Applicable

This plan ends at implementation (file edits). Per [`99-no-auto-commit.mdc`](.cursor/rules/99-no-auto-commit.mdc) and [`01-git-push-prohibition.mdc`](.cursor/rules/01-git-push-prohibition.mdc), committing and pushing each require a separate, explicit user instruction after the edits are reviewed. No PR, merge, or deploy work is in scope.

## Plan Quality Gates

- Target and objective bound: Passed
- Authority resolved: Passed
- Current state understood: Passed
- Requirements and contracts defined: Passed
- Scope bounded: Passed (pyproject.toml/conftest.py explicitly excluded)
- Ownership clear: Passed
- Architecture aligned: Not Applicable (no architecture policy governs doc/comment text)
- Root-cause strategy: Passed
- Task decomposition complete: Passed (4 items, none oversized or fragmented)
- Dependencies valid: Passed (1 parallel wave + 1 sequential verification wave, no cycle)
- Plan items executable: Passed (literal before/after text specified for every edit)
- Contracts preserved or authorized: Passed (no public/persistent contract touched)
- Validation complete: Passed
- Security and risk addressed: Not Applicable (no security-relevant surface)
- Rollback and recovery defined: Passed
- Unknowns and decisions explicit: Passed (A-01, D-01 recorded above)
- Leverage justified: Passed (no speculative automation added)
- No scope drift: Passed
- Plan convergence verified: Passed
- Handoff ready: Passed
- **Overall plan readiness: Passed — plan_status: Ready**

## Minimum Safe Next Action

Execute Wave 1 (PI-01, PI-02, PI-03) in parallel, then Wave 2 (PI-04) — upon the user switching to Agent mode / approving execution. This resolves all 3 findings; no further planning pass has a concrete additional objective.

## Convergence: Converged

One planning pass plus this kernel-formalization pass. No unresolved Critical or High planning defect. No dependency cycle. No material scope ambiguity. No additional high-value planning objective identified.
