<!-- L9META
parent: claude-coding-contract-compiler
layer: reference
role: recursiveharden
version: 2.0.0
updated: 2026-07-12
sources:
  - L9-Recursive-Improvement-Kernel.md (l9_recursive_improvement_enhancement_kernel.v1)
  - prior kernel-recursive-harden.md (v1.0.0, 30 lines)
-->

# Recursive Improvement Kernel  (BINDING for harden mode)

## Activation
Only when an existing contract or skill pack is provided AND the user requests
hardening / improvement / polish / upgrade. Default mode is DRY_RUN.
`write_requires_explicit_authorization: true` — the agent MUST NOT mutate artifacts
until the operator reviews and authorizes the recommended change set.

## Core Laws
1. Improve the artifact, not the appearance of effort.
2. Preserve proven strengths before adding new changes.
3. Fix release blockers before optimizing non-blockers.
4. Every improvement must trace to a defect, risk, gap, leverage gain, or operator benefit.
5. No recursive pass may expand scope without explicit authorization.
6. No improvement is accepted until validated.
7. No regression is acceptable unless explicitly justified and approved.
8. Convergence beats endless polishing.
9. The smallest high-leverage change wins over broad churn.

## DRY_RUN Gate
Default mode: DRY_RUN. In DRY_RUN, the agent produces recommendations and deltas only —
no files are rewritten. Write mode requires an explicit operator statement: "apply" / "execute"
/ "write it". In write mode, each accepted change is validated before the next pass begins.

## Improvement Classes (priority order)
| Priority | Class | Definition |
|---|---|---|
| 1 | `blocker_remediation` | Fixes critical failures: broken imports, missing contracts, stubs, fake validation, missing runbook for large pack |
| 2 | `correctness_improvement` | Functional correctness, schema integrity, execution path, data handling |
| 3 | `completeness_improvement` | Missing required artifacts or missing required depth |
| 4 | `validation_improvement` | Evidence, checks, reports, rerunability, release confidence |
| 5 | `operator_readiness_improvement` | README, RUNBOOK, MANIFEST, VALIDATION, setup, commands, handoff |
| 6 | `maintainability_improvement` | Structure, naming, typed models, adapters, modularity |
| 7 | `leverage_improvement` | Reusable patterns, lower recurring drag, better automation |
| 99 | `cosmetic_improvement` | Formatting, naming polish — allowed ONLY after all higher-priority improvements complete |

## 5 Ordered Passes (minimum required)
Each pass MUST: re-read current artifact state, preserve working components, identify defects
and leverage opportunities, rank improvements by class/priority, apply or recommend the
smallest high-value change, validate the change, check for regressions, update Unknowns.

```
Pass 1: inventory-and-baseline
  - Read every file. Record file count, line count, purpose, known gaps.
  - Produce baseline scorecard (10 dimensions, see Quality Scoring).
  - Do NOT rewrite any file this pass.
  - Label missing inputs UNKNOWN (do not invent).

Pass 2: blocker-remediation + contract-tightening
  - Address priority 1 (blockers) and priority 2 (correctness) only.
  - Fill every UNKNOWN or thin section to full depth. No compression.
  - Record each change: target, defect, action, expected gain.

Pass 3: completeness + validation improvement
  - Add missing required artifacts (priority 3). Improve validation evidence (priority 4).
  - Produce DELTA_REPORT.md with before/after per file.
  - No scope expansion without authorization.

Pass 4: operator readiness + maintainability + entropy reduction
  - Priority 5+6: README/RUNBOOK/MANIFEST/VALIDATION adequacy.
  - Remove dead files, duplicate authority, orphan references.
  - Produce ENTROPYREDUCTIONREPORT.md.

Pass 5: convergence check + final validation
  - Run 6 validation classes (see validation-evidence.md).
  - Produce CONVERGENCE_REPORT.yaml. Check stop conditions.
  - If stop conditions met: produce all required final artifacts.
  - If not met: record reason and continue to Pass 6 (requires authorization).
```

## Stop Conditions (MUST stop when ANY of these hold)
- No material defects remain.
- Next pass improvement estimate < 5%.
- Further improvement requires new scope or external information.
- All hard gates pass and operator readiness passes.
- Two consecutive passes produce materially same output.

## Must-Not-Stop Conditions (MUST NOT stop when ANY of these hold)
- Critical blockers remain.
- Known stubs or placeholders remain.
- Validation is still pass-only or evidence-thin.
- Required docs are missing.
- Pipeline / contract logic is over-thinned.
- Adapters are still generic replacements.

## Improvement Selection Rules
Must prioritize: release blockers, failed validation gates, missing mandatory artifacts,
stubs/placeholders, broken execution paths, operator blockers, high-leverage reusable fixes.

Must deprioritize: formatting-only edits, folder reshuffling without execution gain,
schema compression, pipeline thinning, generic abstraction that removes specificity,
decorative docs, files that do not improve use / validation / maintainability.

## Anti-Regression Requirements
- MUST compare before/after behavior where possible.
- MUST preserve stronger components from prior versions.
- MUST NOT remove detail unless redundant, wrong, or explicitly replaced with stronger structure.
- MUST NOT reduce contract depth.
- MUST NOT reduce pipeline observability.
- MUST NOT replace specific adapters with generic adapters.
- MUST NOT convert rich validation into status-only validation.
- MUST NOT remove operator docs from packs over 10 files.
- MUST NOT reduce importability or package clarity.
- MUST NOT lower validation evidence quality.

## Forbidden Improvement Patterns
- Endless recursive polishing.
- Scope creep disguised as improvement.
- Adding abstractions without reducing real complexity.
- Replacing specific logic with vague generic wrappers.
- Compressing schemas to look cleaner.
- Thinning pipeline stages.
- Adding files not wired into execution, validation, or documentation.
- Changing names without updating references.
- Deleting rich reports in favor of short summaries.
- Claiming convergence without comparing passes.
- Claiming improvement without validation.
- Creating hybrid packs without exact source/component mapping.
- Fixing symptoms while preserving root defects.
- Allowing old defects to reappear in new packaging.

## Hybrid Improvement Policy
When harden mode merges two contract versions:
Allowed when: hybrid clearly beats best single; best components identified; conflicts resolved;
regression risk lower than expected gain.
Forbidden when: hybrid only combines size; increases maintenance without execution gain;
creates duplicate concepts; merges conflicting contracts; cannot be validated.
Required mapping per component: source, reason_selected, conflicts, validation_needed, disposition.

## Quality Scoring (10 dimensions, 0–5 each)
Each score MUST include evidence. Scores MUST compare pre-pass and post-pass.
Unverifiable dimensions MUST be UNKNOWN.
```
execution_readiness, correctness, completeness, validation_strength, operator_readiness,
maintainability, portability, automation_readiness, strategic_leverage, regression_safety
```
Rules: cosmetic-only change cannot increase execution_readiness; change that removes
specificity MUST lower maintainability or correctness unless justified.

## Improvement Validation Gates (all required)
| Gate | Test |
|---|---|
| defect_traceability | PASS only if each improvement maps to a defect, risk, gap, leverage gain, or operator benefit |
| priority | PASS only if release blockers addressed before cosmetic/optional |
| anti_regression | PASS only if no prior strength removed without justified replacement |
| validation_after_change | PASS only if each accepted improvement is validated or marked BLOCKED/UNKNOWN |
| convergence | PASS only if recursive passes stop by a defined stop condition |
| no_scope_creep | PASS only if improvements stay within original scope unless explicitly authorized |
| documentation_update | PASS only if README/RUNBOOK/MANIFEST/VALIDATION updated when changes affect use |
| delta_evidence | PASS only if before/after deltas are recorded with evidence |
| hybrid_mapping | PASS only if hybrid recommendations include exact source/component mapping |
| measurable_gain | PASS only if improvement has expected or observed gain beyond cosmetic change |

## Status Classification (5 values)
- `IMPROVED_EXECUTION_READY` — all blockers resolved, validation passes, no regressions.
- `IMPROVED_WITH_FINDINGS` — material improvement achieved, non-blocking findings remain.
- `BLOCKED_ON_IMPROVEMENT` — required improvement cannot be completed from available evidence.
- `REJECTED_CHANGE_SET` — change introduces regression, reduces specificity, thins schemas, cannot be validated.
- `MINE_FOR_FUTURE` — valuable component, not safe or ready for current artifact.

## Required Final Artifacts (harden mode, all mandatory)
- `IMPROVEMENT_REPORT.md` — objective, baseline, defects targeted, changes, evidence, regression check, next action
- `improvement_log.jsonl` — one row per change: pass_id, change_id, class, target, defect, action, evidence, gain, regression_risk, validation_status, disposition
- `DELTA_REPORT.md` — before/after summary, files changed, functional vs non-functional, removed/added/preserved/rejected, regression notes
- `CONVERGENCE_REPORT.yaml` — passes run, summaries, improvement_ratio_by_pass, remaining defects, unknowns, stop condition triggered, final recommendation
- `ENTROPYREDUCTIONREPORT.md` — what was removed, why, net line delta
- `REGRESSIONGUARD.md` — locked behaviors and how to verify them
- `FINALCONTRACT.md` — output contract
- `VALIDATION.md` — full 6-class validation evidence
- `MANIFEST.md` — all files registered

## Review Output Schema (required for harden mode response)
16 required sections:
executive_improvement_decision, baseline_state, improvement_targets, recursive_pass_log,
before_after_delta, scorecard_delta, accepted_improvements, rejected_improvements,
regressions_checked, remaining_gaps, updated_validation_status, operator_readiness_delta,
final_recommendation, smallest_next_action, unknowns, convergence_block.

## Failure Policy
- Evidence-free → status MUST NOT be IMPROVED_EXECUTION_READY.
- Regression introduced → status MUST be REJECTED_CHANGE_SET unless operator explicitly accepts.
- Scope expands without authorization → status MUST be BLOCKED_ON_IMPROVEMENT.
- Validation cannot confirm improvement → IMPROVED_WITH_FINDINGS or BLOCKED_ON_IMPROVEMENT.
- Only cosmetic changes made → status MUST NOT claim material improvement.
