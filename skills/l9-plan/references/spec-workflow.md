<!-- L9_META
l9_schema: 1
parent: l9-plan
origin: planning-playbook-v3
tags: [spec, playbook, validation]
status: active
version: 3.0.0
updated: 2026-08-02
/L9_META -->

# Spec Workflow — Planning Playbook (spec mode)

Doctrine: Proper planning prevents piss poor performance. A minute spent planning is an hour saved debugging.

**Load** [authority-bindings.md](authority-bindings.md) the same as plan mode. Shells below; fill from fixtures — do not paste catalogs.

## Gather

```text
QUESTIONS:
├── What problem does this solve?
├── Who are the users?
├── What are the constraints?
├── What already exists to leverage?
├── What does success look like?
└── Lesson corpus matches?
```

## Spec shells

1. Load log (required Reads)
2. Overview — problem, solution, success
3. Planning Mode + justification ([ccp-plan-patterns.md](ccp-plan-patterns.md))
4. Files in scope / Files out of scope (**Load:** CCP PLAN.md)
5. Constraints MUST / MUST NOT (**Load:** GMP lock when CHANGE + CCP PLAN)
6. Modification Lock if implementation follows (**Load:** modification-lock.md)
7. Architecture / Components / Data flow
8. Operations (design only; lifecycle auth separate)
9. Assumption + Decision + Unknown registers
10. Acceptance criteria
11. Phases / GMP count
12. Pre-Validation + Validation matrix
13. Plan Definition of Done (**Load:** CCP PLAN plan_quality_gates)
14. Post-implementation Definition of Done (**Load:** DEFINITION_OF_DONE.md + GMP Phase 4–5 names)
15. Kernel Pass Log (**Load:** kernel-pass-pipeline.md)
16. Final Validation · MSNA · Handoff · ADRs consulted

## Validation gates

| Gate | Action | Pass |
|------|--------|------|
| Pre-Validation | Target bind, baseline, lesson corpus, `make pr-check` if code | PASS / Skipped with reason |
| Kernel Pass Log | Five Applied/Blocked on **spec draft** | Complete |
| Final Validation | AC mapped; scanners; honesty; no false lifecycle readiness | PASS |

Omit `make pr-check` only for pure docs — N/A with reason. Never weaken scanners.

## Output location

```text
specs/{project}-spec.md
```

Auto-chain: `l9-ynp` / `/ynp`.
