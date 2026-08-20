---
name: SonarCloud High-Risk Remediation Phase 2
overview: "Systematically remediate 38 high-risk SonarCloud defects (S3776 complexity, S8786 ReDoS, S107 params, S7059 async) across 4 phased waves with security review gates and zero-regression validation."
todos:
  - id: todo-01-baseline
    content: "Verify baseline: on fix/sonarcloud-deferred-safe-issues branch, 15 safe fixes committed, 38 high-risk issues documented"
    status: pending
    phase: preflight
    depends_on: []
  - id: todo-02-phase1-s107
    content: "Phase 1: Refactor 4 functions (8-param → options objects) with backward-compatible shims"
    status: pending
    phase: execute-wave1
    depends_on: [todo-01-baseline]
  - id: todo-03-phase1-validate
    content: "Phase 1 validation: node --check .mjs files, tsc --noEmit, npm test"
    status: pending
    phase: validate-wave1
    depends_on: [todo-02-phase1-s107]
  - id: todo-04-phase2-complexity
    content: "Phase 2: Extract helpers from 8 low-complexity functions (32-40 → <15 cognitive complexity)"
    status: pending
    phase: execute-wave2
    depends_on: [todo-03-phase1-validate]
  - id: todo-05-phase2-validate
    content: "Phase 2 validation: unit tests + integration smoke + complexity metrics"
    status: pending
    phase: validate-wave2
    depends_on: [todo-04-phase2-complexity]
  - id: todo-06-phase3-redos-fuzz
    content: "Phase 3: Create fuzz harness + optimize 6 ReDoS regex patterns with 800k+ equivalence proofs"
    status: pending
    phase: execute-wave3
    depends_on: [todo-05-phase2-validate]
  - id: todo-07-phase3-security
    content: "Phase 3: Security review APPROVED for all ReDoS changes"
    status: pending
    phase: validate-wave3
    depends_on: [todo-06-phase3-redos-fuzz]
  - id: todo-08-phase4-complete
    content: "Phase 4: Eliminate S7059 async constructor + final validation + doc updates"
    status: pending
    phase: converge
    depends_on: [todo-07-phase3-security]
isProject: false
---

# PLAN: SonarCloud High-Risk Issues Remediation - Phase 2

> **Execute via:** [@environment/program-execution](../../environment/program-execution/) → Program Lock/Controller → [@autonomy](../../commands/autonomy.md) (`/autonomy` → `l9-bounded-autonomy`) under Program lease
> **Schema:** `canonical.schema.plan_document.v1` + `l9.plan_document/v4`
> **Status:** `draft` → `executable` when baseline verified + validation gates ready
> **Source JSON:** `docs/sonarcloud-remediation/sonarcloud_remediation_phase2.plan.json`

## Execute via @environment/program-execution + autonomy (required)

**Authority order:**

```text
this .plan.md  (intent / envelope / DAG / success properties)
        │ project
        ▼
@environment/program-execution   HOW work executes (authoritative)
  Blueprint → Program Lock → Controller admit/claim/render/verify/handoff
        │ lease (narrow-never-widen)
        ▼
root autonomy/  +  @autonomy (/autonomy → l9-bounded-autonomy)
  MAY the leased agent act?  (packet, lanes, PR poll) — owns_program_state: false
```

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.sonarcloud.remediation_phase2.v1` |
| title | SonarCloud High-Risk Issues Remediation - Phase 2 (38 Deferred Issues) |
| schema_version | `l9.plan_document/v4` |
| depth | `deep` |
| status | `draft` |
| created_at | 2026-08-16 |
| branch | `fix/sonarcloud-deferred-safe-issues` |
| estimate | 58-71h across 4 PRs over 3-4 weeks |

## Objective

### Mission

Remediate 38 remaining high-risk SonarCloud defects (S3776 cognitive complexity, S8786 ReDoS vulnerabilities, S107 too-many-params, S7059 async constructor) through 4 phased waves with mandatory security review for regex changes and zero behavioral regressions. Each phase independently shippable with full validation gates.

**Preserved contracts:**
- DomainSpec schema backward-compatible
- Validation error structure unchanged
- Evidence collector public API import-compatible
- Regex patterns match-equivalent (fuzz-proven)
- Template script exit codes preserved

### Success properties

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | Baseline branch matches fix/sonarcloud-deferred-safe-issues with 15 safe fixes committed | `repository_state` | `git log --oneline -1` matches expected SHA | true |
| SP-02 | All 38 SonarCloud issues resolved (249 total → 173 Phase 1 → 120 after Phase 2) | `quality_gate` | SonarCloud /api/issues/search shows 38 fewer unresolved issues | true |
| SP-03 | Zero test regressions (100 PASS / 3 BLOCKED pre-existing maintained) | `runtime_behavior` | `npm test` output unchanged failure count | true |
| SP-04 | 6 ReDoS regex changes security-approved with 800k+ fuzz equivalence proofs | `proof_receipt` | SECURITY_REVIEW_REDOS.md status=APPROVED + fuzz reports | true |
| SP-05 | TypeScript compilation clean across all packages | `structural` | `tsc --noEmit` for all tsconfigs exit 0 | true |
| SP-06 | All JavaScript modules syntactically valid | `structural` | `node --check` for all .mjs files exit 0 | true |

## Immutable baseline

| Field | Value |
|-------|-------|
| repository | `Quantum-L9/Website-Bot` |
| branch | `fix/sonarcloud-deferred-safe-issues` |
| commit_sha | *to be locked at execution start* |
| dirty | `false` required |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Execution envelope

### Filesystem

**write_allow:**
- `astro_template/scripts/*.mjs`
- `examples/supplemental-insurance-pros/astro_site/scripts/*.mjs`
- `packages/validation-executor/src/**/*.ts`
- `packages/validation-executor/test/**/*.ts`
- `src/pipeline/validateDomainSpec.ts`
- `src/services/extractJson.ts`
- `src/provisioning/request.ts`
- `src/stages/HandoffEmitterStage.ts`
- `src/validation/validate-generated-site.ts`
- `scripts/validation-executor.ts`
- `scripts/validate-l9-boundaries.mjs`
- `scripts/fuzz_regex_equivalence.mjs` (new)
- `tests/unit/domain-spec-validation.test.ts` (new)
- `tests/unit/extract-json.test.ts` (new)
- `docs/sonarcloud-remediation/**/*.md`
- `docs/sonarcloud-remediation/**/*.yaml`

**write_deny:**
- `contracts/**/*`
- `.github/workflows/l9-*.yml`
- `AGENTS.md`
- `src/intelligence/**/*`
- `src/contracts/**/*`
- `*.lock` files

### Commands

**allow:**
- `npm test`
- `npx tsc --noEmit`
- `node --check <file>`
- `node scripts/fuzz_regex_equivalence.mjs`
- `make pr`
- `git add`, `git commit`, `git push -u origin <branch>`

**deny:**
- `git push --force`
- `git reset --hard`
- `npm install` (except for adding fuzz deps if needed)

### Network

| Field | Value |
|-------|-------|
| mode | `read_only` (for SonarCloud API verification only) |
| allowed_services | `sonarcloud.io` API |

### Autonomous merge

**autonomous_merge:** `false` (COMPATIBILITY forbidden)
**Merge:** only after PE verify/handoff + @autonomy join + L4 plan/PE stack + green+mergeable

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `high` |
| uncertainty | `medium` |
| blast_radius | `high` (Phase 3 ReDoS security-critical) |
| architectural_boundaries_crossed | 3 (validation, provisioning, pipeline) |
| external_systems_touched | 1 (SonarCloud re-analysis) |
| migration_required | false |
| unknown_dependency_count | 5 (see unknowns) |

## Scope

**In scope:**
- S3776 cognitive complexity reduction (23 total: 8 low-hanging phase 2, 15 deferred to future)
- S8786 ReDoS regex optimization with security review (6 patterns)
- S107 function signature migration to options objects (4 functions)
- S7059 async constructor elimination (1 occurrence)
- S2486, S4036 advisory template fixes (already completed in phase 1)
- Unit test coverage for refactored functions
- Fuzz-test harness for regex equivalence
- Security review process
- Documentation updates

**Out of scope:**
- S3776 high complexity 40-79 (15 issues deferred to dedicated Phase 4)
- Upstream l9-ci-core workflow fixes (20 issues, separate repo)
- False-positive issues (3 confirmed)
- Performance optimization beyond compliance
- Test framework migrations
- CI/CD pipeline modifications
- SonarCloud rule configuration

## Pre-validation

| id | command_or_action | pass_criteria | status |
|----|-------------------|---------------|--------|
| baseline-branch | `git fetch origin && git status` | On fix/sonarcloud-deferred-safe-issues, 15 safe fixes committed | passed |
| baseline-sonar-status | Review `SONARCLOUD_ISSUE_REGISTER.yaml` | 53 REMAINS_DEFERRED documented (38 in-repo + 15 fixed) | passed |
| test-suite-green | `npm test` | 100 PASS / 3 BLOCKED pre-existing | pending |
| existing-coverage | Identify coverage for target functions | ≥70% line coverage | pending |
| security-review-process | Confirm security reviewer availability | Reviewer identified or self-review protocol | pending |

## Execution DAG (phased waves)

### Phase 1: S107 Options Objects (Wave 1)

**Critical path:** `phase1-s107-template-lib` → `phase1-s107-example-lib`, `phase1-s107-validation-framework`, `phase1-s107-evidence-collector` → `phase1-validate`

**TODOs:**

1. **phase1-s107-template-lib** (leverage_rank: 1)
   - Task: Refactor `astro_template/scripts/lib.mjs:49` `result()` from 8 params → options object with backward-compatible shim
   - Files: `astro_template/scripts/lib.mjs`, 6 verify scripts
   - Effort: 2h | Risk: low | Deps: []

2. **phase1-s107-example-lib** (leverage_rank: 5)
   - Task: Apply same refactor to duplicated `examples/.../lib.mjs:49`
   - Files: `examples/supplemental-insurance-pros/astro_site/scripts/lib.mjs`
   - Effort: 30m | Risk: low | Deps: [phase1-s107-template-lib]

3. **phase1-s107-validation-framework** (leverage_rank: 6)
   - Task: Refactor `validation-framework.mjs:13` `validate()` 8 params → options
   - Files: `astro_template/scripts/validation-framework.mjs`
   - Effort: 1h | Risk: low | Deps: []

4. **phase1-s107-evidence-collector** (leverage_rank: 7)
   - Task: Refactor `EvidenceCollector.ts:86` from 8 params → `EvidenceEntryOptions` interface
   - Files: `packages/validation-executor/src/core/EvidenceCollector.ts`, callers, tests
   - Effort: 3h | Risk: medium | Deps: []

5. **phase1-validate** (leverage_rank: 8) **[CHECKPOINT CP1]**
   - Task: Validate Phase 1: `node --check` .mjs, `tsc --noEmit`, `npm test`
   - Blocker: checkpoint_validation
   - Effort: 30m | Risk: low | Deps: [all phase 1]

### Phase 2: S3776 Low Complexity (Wave 2)

**Critical path:** `phase2-s3776-validate-spec-low` → `phase2-s3776-validate-spec-routes` → `phase2-s3776-validate-spec-provision` → parallel tasks → `phase2-validate`

**TODOs:**

6. **phase2-s3776-validate-spec-low** (leverage_rank: 2)
   - Task: Extract validation helpers from `validateDomainSpec.ts:75` (complexity 35 → <15)
   - Files: `src/pipeline/validateDomainSpec.ts`, `tests/unit/domain-spec-validation.test.ts` (new)
   - Effort: 4h | Risk: high | Deps: [phase1-validate]
   - Pattern: Extract `validateBusiness()`, `validateRoutes()`, `validateDeploy()`

7. **phase2-s3776-validate-spec-routes** (leverage_rank: 3)
   - Task: Extract route validation from `validateDomainSpec.ts:119` (complexity 38 → <15)
   - Files: `src/pipeline/validateDomainSpec.ts`
   - Effort: 3h | Risk: high | Deps: [phase2-s3776-validate-spec-low]

8. **phase2-s3776-validate-spec-provision** (leverage_rank: 4)
   - Task: Extract provision validation from `validateDomainSpec.ts:153` (complexity 40 → <15)
   - Files: `src/pipeline/validateDomainSpec.ts`
   - Effort: 3h | Risk: high | Deps: [phase2-s3776-validate-spec-routes]

9-12. **phase2-s3776-cli-low**, **phase2-s3776-validator-low**, **phase2-s3776-extract-json**, **phase2-s3776-example-verify-smoke**
   - Tasks: Extract helpers from CLI, validators, extractJson, template smoke test
   - Effort: 5h + 3h + 2h + 2h | Risk: high/medium/medium/low
   - Deps: [phase1-validate]

13. **phase2-validate** (leverage_rank: 13) **[CHECKPOINT CP2]**
    - Task: Unit tests green, integration smoke, complexity metrics verified
    - Blocker: checkpoint_validation
    - Effort: 1h | Risk: low | Deps: [all phase 2]

### Phase 3: S8786 ReDoS Security (Wave 3)

**Critical path:** `phase3-redos-fuzz-harness` → 6 regex optimizations (sequential) → `phase3-security-review` → `phase3-validate`

**TODOs:**

14. **phase3-redos-fuzz-harness** (leverage_rank: 14)
    - Task: Create `scripts/fuzz_regex_equivalence.mjs` for 800k+ test case generation
    - Files: `scripts/fuzz_regex_equivalence.mjs` (new)
    - Effort: 3h | Risk: low | Deps: [phase2-validate]

15-20. **phase3-redos-secure-exec-{110,113}**, **phase3-redos-e2e-engine**, **phase3-redos-handoff-emitter**, **phase3-redos-request**, **phase3-redos-validate-site**
    - Tasks: Optimize 6 ReDoS regex patterns with atomic grouping + fuzz equivalence proofs
    - Files: 6 source files + 6 proof documents
    - Effort: 4h each | Risk: high | Sequential deps
    - Pattern: Replace nested quantifiers with atomic groups, generate equivalence proof

21. **phase3-security-review** (leverage_rank: 21) **[CHECKPOINT CP4]**
    - Task: Security review APPROVED for all 6 ReDoS changes + fuzz evidence
    - Files: `docs/sonarcloud-remediation/SECURITY_REVIEW_REDOS.md`
    - Effort: 2h | Risk: irreversible | Deps: [all 6 regex tasks]
    - **CRITICAL:** BLOCK merge if not APPROVED

22. **phase3-validate** (leverage_rank: 22) **[CHECKPOINT CP3]**
    - Task: Security APPROVED, tests green, fuzz evidence documented, `make pr` PASS
    - Blocker: checkpoint_validation
    - Effort: 1h | Risk: high | Deps: [phase3-security-review]

### Phase 4: Final Convergence (Wave 4)

**Critical path:** `phase4-s7059-evidence-collector` → `phase4-validate` → `phase4-doc-update`

**TODOs:**

23. **phase4-s7059-evidence-collector** (leverage_rank: 23)
    - Task: Refactor `EvidenceCollector.ts:31` async constructor → static factory pattern
    - Files: `packages/validation-executor/src/core/EvidenceCollector.ts`, callers
    - Effort: 2h | Risk: medium | Deps: [phase1-s107-evidence-collector]

24. **phase4-validate** (leverage_rank: 24) **[CHECKPOINT CP5]**
    - Task: All 38 issues closed on SonarCloud, zero regressions, `make pr` PASS
    - Blocker: checkpoint_validation
    - Effort: 1h | Risk: low | Deps: [phase4-s7059-evidence-collector]

25. **phase4-doc-update** (leverage_rank: 25)
    - Task: Update remediation docs with Phase 4 deferral notes (15 high-complexity functions)
    - Files: `REMAINING_HIGH_RISK_ANALYSIS.md`, `SONARCLOUD_REMEDIATION_REPORT.md`, `SONARCLOUD_ISSUE_REGISTER.yaml`
    - Effort: 1h | Risk: low | Deps: [phase4-validate]

## Checkpoints (validation gates)

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| CP1-phase1-tests | phase1-validate | npm test 100 PASS / 3 BLOCKED, tsc clean | Rollback Phase 1, do not proceed to Phase 2 |
| CP2-phase2-complexity | phase2-validate | Complexity metrics <15 for target functions, integration tests PASS | Rollback complexity refactors, add tests, do not proceed to Phase 3 |
| CP3-redos-fuzz-equivalence | phase3-redos-validate-site | All 6 regex fuzz reports 0 differences over 800k+ cases | BLOCK Phase 3, do not submit for security review until proven |
| CP4-security-approval | phase3-security-review | SECURITY_REVIEW_REDOS.md status=APPROVED | BLOCK merge, address feedback, re-fuzz if changed, do not deploy |
| CP5-sonarcloud-closure | phase4-validate | SonarCloud API confirms 38 issues closed | Investigate non-closure, verify branch analysis, manual review |

## Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1-phase1-complete | 4 S107 functions → options objects, backward-compatible, tests green | Safe API pattern for future, Phase 2 work |
| M2-phase2-complete | 8 low-complexity S3776 functions refactored (32-40 → <15) | Validates approach for remaining 15 high-complexity in Phase 4 |
| M3-phase3-security-approved | 6 ReDoS regexes optimized, 800k+ fuzz PASS, security APPROVED | Production deployment, closes HIGH SECURITY RISK |
| M4-phase4-complete | S7059 eliminated, 38 issues closed, SonarCloud validates | 249 → 120 issues, plan for 15 critical remaining |

## Stress test (disconfirming questions)

1. **What if** extracted validation helpers alter error message formats that downstream systems parse?
   - **Mitigation:** Probe for external error consumers; preserve exact format if found

2. **What if** ReDoS regex optimizations change matching on edge cases in production data?
   - **Mitigation:** Generate fuzz corpus from production samples; 800k+ minimum; security review includes prod validation

3. **What if** options-object migration breaks external callers via dynamic require/reflection?
   - **Mitigation:** Keep deprecated 8-param shims with console.warn for 2+ releases; search for dynamic calls

4. **What if** existing test coverage insufficient, refactored functions break but tests still pass?
   - **Mitigation:** Pre-inject intentional bugs, verify tests catch them; add failing-then-passing tests if not

5. **What if** security reviewer unavailable or blocks all 6 regex changes?
   - **Mitigation:** Self-review protocol: fuzz evidence + security checklist + staged rollout + async post-merge review

**Assumed false if:**
- Validation error messages NOT consumed by external parsers
- No dynamic calls to 8-param functions via apply/reflection
- Existing tests provide ≥70% coverage for refactor targets
- ReDoS patterns NOT in user-provided config or dynamically loaded
- Security review SLA within 1-2 days or self-review acceptable
- SonarCloud re-analysis triggers automatically on merge

**Blast radius:**
- Phase 1: Template breakage affects local validation only
- Phase 2: Validator bugs could break site generation for all clients
- **Phase 3: Regex bugs → SECURITY VULNERABILITIES or AVAILABILITY (ReDoS in production)**
- Phase 4: Factory bugs affect validation-executor instantiation

## Rollback

**Supported:** `true`  
**Automatic:** `false`  
**Approval required:** `true`  
**Trigger:** baseline drift, blocking property fail, envelope breach, security incident

**Strategies:**

| domain | mode | notes |
|--------|------|-------|
| code | `revert_commit` per phase | Each phase independently revertible via `git revert <phase-sha>` |
| Phase 1 | Restore 8-param signatures | Revert options-object changes |
| Phase 2 | Restore monolithic validators | Revert helper extractions |
| **Phase 3 (CRITICAL)** | **Emergency revert all regex** | **If ANY production security incident, restore original patterns immediately** |
| Phase 4 | Restore constructor pattern | Revert static factory |

**Irreversible operations:** None

**Rollback verification:** `npm test` + `tsc --noEmit` + `make pr` PASS after revert

## Leverage analysis

**Ranked TODOs by unlock value:**
1. phase1-s107-template-lib (shared root cause: 8-param signature across 7+ files)
2. phase2-s3776-validate-spec-low (shared root cause: nested validation without helpers)
3. phase2-s3776-validate-spec-routes (same shared cause)
4. phase2-s3776-validate-spec-provision (same shared cause)
5-25. [remaining in dependency order]

**Shared root causes:**
1. 8-param function signatures (S107) - `result()` and `validate()` used across 7+ files
2. Nested validation logic without helper extraction (S3776) - 3 functions in validateDomainSpec.ts
3. Nested quantifiers in regexes (S8786) - 6 security-critical patterns need atomic grouping

**Deletions/consolidations (future):**
- Consolidate duplicated lib.mjs between template and examples
- Remove 8-param legacy shims after 1-2 release deprecation

## Risks and mitigation

| risk | mitigation |
|------|------------|
| Phase 2 validator regression in edge case validation | Add comprehensive unit tests before refactoring; run E2E with 3+ domain specs; compare output byte-for-byte |
| Phase 3 ReDoS changes alter matching on production edge cases | Generate fuzz corpus from production samples; 800k+ cases; security review includes prod validation |
| Security reviewer unavailable, stalling Phase 3 for weeks | Self-review protocol: fuzz equivalence + security checklist + staged rollout + async post-merge review |
| Existing test coverage insufficient (false positive quality) | Pre-inject bugs, verify tests catch them; require mutation testing or manual break-test |
| Phase 1 API-breaking changes in external caller scripts | Keep deprecated shims for 2+ releases; document in CHANGELOG; search for dynamic calls |
| SonarCloud doesn't re-analyze or reports false negatives | Manual /api/issues/search review; trigger re-analysis manually; document closure status |

## Unknowns

| id | question | decision_effect | resolution |
|----|----------|-----------------|------------|
| U1-external-callers | External scripts calling 8-param result()? | If yes: keep shim permanently or extend deprecation | probe |
| U2-security-reviewer-identity | Who reviews ReDoS? Availability SLA? | If unavailable: self-review protocol or defer Phase 3 | ask |
| U3-prod-data-regex-coverage | Production data samples for fuzz corpus? | If yes: high-confidence testing; If no: synthetic edge cases | probe |
| U4-validation-error-consumers | External systems parsing validation errors? | If yes: must preserve exact format; If no: can improve | probe |
| U5-mutation-test-availability | Mutation testing (Stryker) available? | If yes: use for test quality; If no: manual break-test | probe |

## Final validation

| id | command | pass_criteria | status |
|----|---------|---------------|--------|
| FV1-all-phases-tests | `npm test` | 100 PASS / 3 BLOCKED (no new failures), exit 0 | pending |
| FV2-typescript-clean | `npx tsc --noEmit -p tsconfig*.json` | No type errors | pending |
| FV3-javascript-syntax | `for f in **/*.mjs; do node --check "$f"; done` | All .mjs parse successfully | pending |
| FV4-regex-equivalence | `node scripts/fuzz_regex_equivalence.mjs --verify-all` | 0 differences, ≥800k cases each | pending |
| FV5-security-review | `grep 'Status: APPROVED' docs/.../SECURITY_REVIEW_REDOS.md` | Security review APPROVED | pending |
| FV6-sonarcloud-closure | SonarCloud API query | Issue count reduced by 38 | pending |
| FV7-make-pr | `make pr` | All pre-PR checks PASS | pending |

## Doc/Root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| REMAINING_HIGH_RISK_ANALYSIS.md | update | [phase4-doc-update] | Document Phase 2-4 completion, Phase 4 deferral |
| SONARCLOUD_REMEDIATION_REPORT.md | update | [phase4-doc-update] | Update fixed count 173 → 211, add Phase 2-4 summary |
| SONARCLOUD_ISSUE_REGISTER.yaml | update | [phase4-validate] | Change disposition REMAINS_DEFERRED → FIXED_PENDING for 38 issues |
| README.md | n_a | | Internal code quality, no user-facing changes |
| AGENTS.md | n_a | | No agent instruction changes |

## GMP handoff

**may_modify:** All files listed in execution envelope write_allow  
**must_not_modify:** contracts/**, .github/workflows/l9-*.yml, AGENTS.md, src/intelligence/**, src/contracts/**  
**preserved_contracts:** DomainSpec schema backward-compatible, validation error structure unchanged, evidence collector API compatible, regex match-equivalent, template exit codes preserved  
**validation_commands:** npm test, tsc --noEmit, node --check, fuzz_regex_equivalence.mjs, make pr

## Convergence

| Field | Value |
|-------|-------|
| status | `partial` (pending runtime validation + unknown resolution) |
| remaining_unknown_ids | U1-U5 (to be resolved during phased execution) |
| next_skill | `l9-ynp` (prioritize next action) |
| implementation_ready | `false` (pending baseline lock + pre-validation) |

**Stop reason:** Plan ready for execution, pending runtime validation gates and unknown resolution during implementation. Pre-validation checks require execution context. All final validations pending until implementation. 5 unknowns resolved via probe/ask during phases.

**Next action:** When baseline locked + preflight PASS + status=`executable`, attach [@environment/program-execution](../../environment/program-execution/) + [@autonomy](../../commands/autonomy.md) to execute phased waves with checkpoint gates between each phase.

---

## Machine artifact reference

**Source JSON:** `/Users/macm2/Website-Bot-1/docs/sonarcloud-remediation/sonarcloud_remediation_phase2.plan.json`

**Validator:** `python3 .claude/skills/l9-plan/scripts/validate_plan_document.py docs/sonarcloud-remediation/sonarcloud_remediation_phase2.plan.json`

**Status:** ✅ PASS (validated 2026-08-16)

**Estimate:** Phase 1: 6-8h. Phase 2: 20-25h. Phase 3: 28-32h (includes security review). Phase 4: 4-6h. **Total: 58-71h** spread across 4 PRs over 3-4 weeks with checkpoint validations between phases.
