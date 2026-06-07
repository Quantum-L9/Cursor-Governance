<!-- L9_META
skill_schema: 1
parent: l9-recursive-optimization
layer: reference
role: validation_contract
tags: [recursive, validation, quality_gates]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-06-06
/L9_META -->

# Validation Checklist

## Purpose

Fail-closed gates before delivering recursive optimization output.

## Preflight

- [ ] Artifact group or scope provided (or STOP)
- [ ] Mode selected (align / improve / optimize)
- [ ] Implement-vs-report boundary confirmed

## Alignment Gates

- [ ] Context lock completed (pass 1)
- [ ] Applicable L9 passes run or marked N/A with reason
- [ ] Every violation has id, severity, evidence, correction
- [ ] Unknowns listed — not invented
- [ ] Correction roadmap ordered by dependency
- [ ] No file mutations in align-only mode

## Improvement Gates

- [ ] All 10 improvement passes addressed or N/A documented
- [ ] Source intent preserved
- [ ] No unsupported scope added
- [ ] Constraints strengthened not weakened
- [ ] Complete revised pack returned when pack-based
- [ ] Cross-file references valid

## Convergence Gates

- [ ] Convergence block present with all required fields for mode
- [ ] `convergence_status` matches actual state
- [ ] `minimum_safe_next_action` is one concrete step
- [ ] No intermediate pass dumps unless user requested

## Zero-Stub Gates

Reject delivery if:

- [ ] placeholder sections presented as complete
- [ ] TODO-as-deliverable in improved artifacts
- [ ] fake validation or pretend compliance
- [ ] partial pack when complete pack required
- [ ] alignment claims converged with unresolved critical violations (unless user waived)

## Design Principles

- [ ] **Composable** — chains with `l9-skill-compiler`, `l9-gmp-protocol`, `l9-gap-analysis`
- [ ] **Fail fast** — missing input surfaced before long passes
- [ ] **Idempotent** — align-only re-run on same source yields same violations
- [ ] **Self-documenting** — output states mode, passes, next action
