<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [spec, validation]
status: active
version: 4.0.0
updated: 2026-08-12
/L9_META -->

# Spec Workflow

Generate a complete spec before implementation. Prefer emitting a PLAN_DOCUMENT with `mode: spec` plus narrative sections below. Validate with `validate_plan_document.py`.

## Gather context

```text
QUESTIONS:
├── What problem does this solve?
├── Who are the users?
├── What are the constraints?
├── What already exists to leverage?
├── What does success look like?
└── Which root/agent docs would go stale if this ships?
```

## Spec sections

1. Overview — problem, solution, success criteria
2. Constraints — must / must not / should
3. Architecture — diagram
4. Components — table
5. Data flow
6. Operations — deploy, monitor, rollback
7. Doc / Root Surface Impact
8. Risks
9. Acceptance criteria
10. Phases
11. Pre-Validation (mandatory)
12. Final Validation (mandatory)
13. Stress Test + Leverage + Convergence + GMP Handoff

Unjustified omission of Doc / Root Surface Impact fails closed.
Auto-chain: `l9-ynp` (forge or gmp).
