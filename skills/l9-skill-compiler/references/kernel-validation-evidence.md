<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: reference
role: validation-evidence-kernel
version: 2.0.0
status: active
-->

# Validation Evidence Kernel

## Six classes

1. Structural: files, archive shape, references, manifests.
2. Contract: frontmatter, schemas, required fields, authority and tier rules.
3. Execution: scripts compile and run; tests and smoke checks execute.
4. Evidence: each pass claim has inspectable output.
5. Operator: README, runbook, commands, failure paths, and handoff are usable.
6. Regression: compare the current pack to the prior baseline when one exists.

## Evidence matrix

Each check records `check_id`, class, target, method, expected, actual, status, evidence, severity, and remediation. Status is `PASS`, `FAIL`, `BLOCKED`, `UNKNOWN`, or `NOT_APPLICABLE`.

## Forbidden patterns

- pass claimed because a report file exists
- tests described but not run
- source files counted but not inspected
- `Unknown` silently converted to pass
- regression skipped despite an available baseline
- operator readiness inferred from file count alone

Any forbidden pattern blocks an exemplary claim.
