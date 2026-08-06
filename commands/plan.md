---
name: plan
version: "1.2.0"
description: "Create deep execution plan before action (pre/final validation, doc/root surface impact, milestones, checkpoints, checklist)"
auto_chain: ynp
---

# /plan — Execution Planning

## WHAT IT DOES

Create a structured plan before implementation. Delegates template authority to skill `l9-plan` → `skills/l9-plan/references/plan-workflow.md` (SSOT).

1. Pre-Validate (mandatory)
2. Define objective + falsifiable success
3. Identify scope
4. List TODO items with depth
5. Doc / Root Surface Impact (mandatory) — README, AGENTS.md, and related surfaces; Update TODOs or N/A with reason
6. Map dependencies, milestones, checkpoints
7. Build checklist (include doc/root items or N/A)
8. Estimate effort + risks
9. Define Final Validation (mandatory; `make pr-check` when code in scope)
10. Auto-chain to `/ynp`

Planning-only — do not edit files, commit, or push from `/plan`.

---

## EXECUTION

Follow skill `l9-plan`. Required sections (fail-closed if any missing):

1. Objective (+ Success)
2. Scope in/out
3. Pre-Validation
4. TODO Plan (+ Depth)
5. Doc / Root Surface Impact
6. Dependencies
7. Milestones
8. Checkpoints
9. Checklist
10. Risks
11. Estimate
12. Final Validation

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

### Doc / Root Surface Impact (mandatory)
| Surface | Action | Files / notes |
|---------|--------|---------------|
| README.md / AGENTS.md / … | Update \| N/A | {TODO ids or reason} |

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
- [ ] Doc / Root Surface Impact recorded
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
| Doc surfaces | Impact table complete | Update or N/A with reason |
```

→ **Auto-chains to /ynp** (recommends /gmp or /forge)

--- End Command ---
