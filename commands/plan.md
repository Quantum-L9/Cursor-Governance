---
name: plan
version: "1.1.0"
description: "Create deep execution plan before action (pre/final validation, milestones, checkpoints, checklist)"
auto_chain: ynp
---

# /plan — Execution Planning

## WHAT IT DOES

Create a structured plan before implementation. Delegates template authority to skill `l9-plan` → `skills/l9-plan/references/plan-workflow.md` (SSOT).

1. Pre-Validate (mandatory)
2. Define objective + falsifiable success
3. Identify scope
4. List TODO items with depth
5. Map dependencies, milestones, checkpoints
6. Build checklist
7. Estimate effort + risks
8. Define Final Validation (mandatory; `make pr-check` when code in scope)
9. Auto-chain to `/ynp`

Planning-only — do not edit files, commit, or push from `/plan`.

---

## EXECUTION

Follow skill `l9-plan`. Required sections (fail-closed if any missing):

1. Objective (+ Success)
2. Scope in/out
3. Pre-Validation
4. TODO Plan (+ Depth)
5. Dependencies
6. Milestones
7. Checkpoints
8. Checklist
9. Risks
10. Estimate
11. Final Validation

### Gate commands (governed workspaces)

```bash
# Changed-files scanners only — does NOT push or commit
make pr-check
# alias:
make pr
```

Make is case-sensitive: use lowercase `pr-check` / `pr`, not `PR-check`.

---

## OUTPUT

```markdown
## PLAN: {title}

### Objective
{what and why}
**Success:** {falsifiable criteria}

### Scope
**In:** {list}
**Out:** {list}

### Pre-Validation (mandatory)
| Check | Command / action | Pass criteria |
|-------|------------------|---------------|
| … | `make pr-check` (when code in scope) | PASS; no commit/push |

### TODO Plan
| # | Task | Files | Effort | Risk |
|---|------|-------|--------|------|

### Depth
{contracts preserved, evidence, root-cause notes}

### Dependencies
{graph}

### Milestones
| Milestone | Outcome | Unlocks |
|-----------|---------|---------|

### Checkpoints
| CP | After | Evidence required | No-go action |
|----|-------|-------------------|--------------|

### Checklist
- [ ] …
- [ ] Final Validation PASS

### Risks
| Risk | Mitigation |
|------|------------|

### Estimate
**Total:** {time}
**GMPs:** {count}

### Final Validation (mandatory)
| Check | Command | Pass criteria |
|-------|---------|---------------|
| Clean scanners | `make pr-check` (when code in scope) | PASS; no commit/push |
```

→ **Auto-chains to /ynp** (recommends /gmp or /forge)

--- End Command ---
