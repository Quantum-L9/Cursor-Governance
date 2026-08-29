<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [plan, todo, validation, projection]
status: active
version: 4.0.0
updated: 2026-08-12
/L9_META -->

# Plan Workflow — Markdown Projection

SSOT is `schemas/plan-document.schema.json`. This file is the human projection template.
Emit JSON first; validate; then render (or hand-write matching sections).

## Output format

```markdown
## PLAN: {title}

### Objective
{objective}
**Success:** {success_criteria}

### Scope
**In:** {scope.in}
**Out:** {scope.out}

### Pre-Validation (mandatory)
| Check | Command / action | Pass criteria | Status |
|-------|------------------|---------------|--------|

### TODO Plan
| # | Task | Files | Effort | Risk | Deps | Leverage |
|---|------|-------|--------|------|------|----------|

### Critical Path
{ordered todo ids}

### Depth
{behavioral notes, contracts preserved}

### Stress Test
- Disconfirming: ...
- Assumed false if: ...
- Blast radius: ...
- Rollback: ...

### Leverage
- Ranked todos: ...
- Shared causes: ...
- Deletions/consolidations: ...

### Doc / Root Surface Impact (mandatory)
| Surface | Action | Files / notes |
|---------|--------|---------------|

### Dependencies
{task graph}

### Milestones
| Milestone | Outcome | Unlocks |
|-----------|---------|---------|

### Checkpoints
| CP | After | Evidence required | No-go action |
|----|-------|-------------------|--------------|

### Checklist
- [ ] ...

### Risks
| Risk | Mitigation |
|------|------------|

### Unknowns
| ID | Question | Effect | Resolution |
|----|----------|--------|------------|

### Estimate
**Total:** {time}

### Final Validation (mandatory)
| Check | Command | Pass criteria | Status |
|-------|---------|---------------|--------|

### Convergence
status / remaining unknowns / next_skill / stop_reason

### GMP Handoff
may_modify / must_not_modify / preserved_contracts / validation_commands
```

## Gate rules

- Every plan must validate via `scripts/validate_plan_document.py`.
- Code-editing plans must include `.pre-commit-config.yaml` in final_validation.
- Never weaken scanners to obtain PASS.
- Do not mutate product code from plan mode.
