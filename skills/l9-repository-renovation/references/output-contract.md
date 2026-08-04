<!-- L9_META
layer: reference
role: output_contract
tags: [artifacts, reports, contract]
status: active
-->
# Output Contract

A complete renovation run produces:

1. `repository-audit.before.json`
2. `renovation-contract.json`
3. `RENOVATION_PLAN.md`
4. implemented repository files
5. `validation-evidence.json`
6. `repository-audit.after.json`
7. `renovation-delta.json`
8. `RENOVATION_DELTA.md`
9. `pr-pack-validation.json`
10. `PR_BODY.md`
11. one draft PR, or a blocked-pack report

## Audit finding

Each finding contains id, class, severity, confidence, summary, consequence, evidence, and recommendation.

## Renovation contract

The contract contains immutable baseline, authority decisions, scope, preserved behavior, phases, validation matrix, acceptance criteria, rollback, PR policy, and unknowns.

## Validation evidence

Each command record contains command, working directory, start/end timestamps, duration, exit code, status, and bounded output. Success is never pre-filled.

## Delta

The delta reports resolved, remaining, introduced, and severity movement. It must not equate fewer findings with correctness.

## PR body

The PR body explains operational defect, target authority model, implementation, validation, risk, rollback, compatibility, and remaining debt.
