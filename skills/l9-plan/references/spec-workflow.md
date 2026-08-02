<!-- L9_META
l9_schema: 1
parent: l9-plan
origin: migrated-from spec command v7.1.0
tags: [spec, specification, architecture, acceptance, validation, kernels]
status: active
version: 2.2.0
updated: 2026-08-02
/L9_META -->

# Spec Workflow — Specification Generator

Generate complete spec before implementation.

Doctrine: Proper planning prevents piss poor performance. A minute spent planning is an hour saved debugging.

Orchestration: [kernel-pass-pipeline.md](kernel-pass-pipeline.md). Patterns: [ccp-plan-patterns.md](ccp-plan-patterns.md).

## Gather context

```text
QUESTIONS:
├── What problem does this solve?
├── Who are the users?
├── What are the constraints?
├── What already exists to leverage?
├── What does success look like?
└── Any matches in learning/failures/repeated-mistakes.md?
```

## Spec sections

1. Overview — problem, solution, success criteria
2. Planning Mode + justification (Quick/Standard/Deep/Release)
3. Constraints — must / must not / should
4. Architecture — diagram
5. Components — table
6. Data flow
7. Operations — deploy, monitor, rollback (design only; lifecycle auth separate)
8. Risks; Unknown register; Decision register
9. Acceptance criteria (checkboxes) — Definition of Done language: complete, validated, no stubs, contracts preserved
10. Phases — scope and GMP count
11. Pre-Validation (mandatory) — baseline gates before build
12. Validation matrix — targeted / integration / final; structural ≠ behavioral
13. Final Validation (mandatory) — post-build gates
14. Kernel Pass Log (mandatory) — five-kernel pipeline on the **spec draft**
15. Minimum Safe Next Action + handoff profile

## Validation gates (mandatory)

### Pre-Validation

Before implementation begins, record:

| Check | Command / action | Pass criteria |
|-------|------------------|---------------|
| Target bind | Resolve authorized roots | Unambiguous scope |
| Baseline | Inventory current behavior/contracts | Evidence captured |
| Lesson corpus | `learning/failures/repeated-mistakes.md` when accessible | Matches or `None matched` |
| Clean gate (code in scope) | `make pr-check` | PASS — changed-files scanners; **no commit, no push** |

### Validation matrix

| Level | Check | Structural vs behavioral | Pass criteria |
|-------|-------|--------------------------|---------------|
| Targeted | … | … | … |
| Integration | … | … | … |
| Final | DoD / acceptance | behavioral + structural | AC met or waived |
| Final | `make pr-check` (when code in scope) | scanners | PASS; no commit/push |

### Final Validation

Before claiming the spec is execution-complete / implementation-ready:

| Check | Command / action | Pass criteria |
|-------|------------------|---------------|
| Acceptance | Map AC to evidence | All in-scope AC met or waived |
| Clean gate (code in scope) | `make pr-check` | PASS; **no commit, no push** unless user explicitly asks |
| Honesty | Status labels | Passed / Failed / Skipped / N/A / Unknown only |
| Lifecycle honesty | Readiness claim | Implementation-ready ≠ MergeReady / ReleaseReady |

### Kernel Pass Log (mandatory)

Apply [kernel-pass-pipeline.md](kernel-pass-pipeline.md) to the **spec draft** before presenting as ready. Five rows: Improve → Leverage → Recursive Alignment → Recursive Leverage → Validate & Repair. Status `Applied` \| `Blocked` only.

Omit `make pr-check` only when the spec covers pure planning/docs with no code edits — mark N/A with reason. Never weaken scanners to obtain PASS.

Do not claim Done while any applicable mandatory gate is Failed or Unknown.

## Output location

```text
specs/{project}-spec.md
```

## Future: IR engine integration

When wired, `SemanticCompiler` / `UnifiedController.compile_only()` can pre-populate constraints from NL during gather context. **Status:** not yet wired — manual gather only.

Auto-chain recommendation: load `l9-ynp` (recommends forge or gmp).
