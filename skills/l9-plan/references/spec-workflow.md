<!-- L9_META
l9_schema: 1
parent: l9-plan
origin: migrated-from spec command v7.1.0
tags: [spec, specification, architecture, acceptance, validation, doc-surface]
status: active
version: 2.2.0
updated: 2026-08-06
/L9_META -->

# Spec Workflow — Specification Generator

Generate complete spec before implementation.

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
7. Doc / Root Surface Impact — README, AGENTS.md, and related surfaces (Update paths or N/A with reason)
8. Risks
9. Acceptance criteria (checkboxes; include doc-surface AC when contracts change)
10. Phases — scope and GMP count
11. Pre-Validation (mandatory) — baseline gates before build
12. Final Validation (mandatory) — post-build gates

## Validation gates (mandatory)

### Pre-Validation

Before implementation begins, record:

| Check | Command / action | Pass criteria |
|-------|------------------|---------------|
| Target bind | Resolve authorized roots | Unambiguous scope |
| Baseline | Inventory current behavior/contracts | Evidence captured |
| Doc / Root Surface Impact | Probe README/AGENTS (+ present peers) | Update list or N/A with reason |
| Clean gate (code in scope) | `make pr-check` | PASS — changed-files scanners; **no commit, no push** |

### Final Validation

Before claiming the spec is execution-complete / implementation-ready:

| Check | Command / action | Pass criteria |
|-------|------------------|---------------|
| Acceptance | Map AC to evidence | All in-scope AC met or waived |
| Doc surfaces | Scheduled updates applied or N/A still valid | No stale agent/human contract docs |
| Clean gate (code in scope) | `make pr-check` | PASS; **no commit, no push** unless user explicitly asks |
| Honesty | Status labels | Passed / Failed / Skipped / N/A / Unknown only |

Omit `make pr-check` only when the spec covers pure planning/docs with no code edits — mark N/A with reason. Never weaken scanners to obtain PASS.

Unjustified omission of Doc / Root Surface Impact fails closed. Prefer `l9-update-agent-docs` / `l9-wire-skill-into-repo` at implementation for agent/registry rewrites.

## Output location

```text
specs/{project}-spec.md
```

## Future: IR engine integration

When wired, `SemanticCompiler` / `UnifiedController.compile_only()` can pre-populate constraints from NL during gather context. **Status:** not yet wired — manual gather only.

Auto-chain recommendation: load `l9-ynp` (recommends forge or gmp).
