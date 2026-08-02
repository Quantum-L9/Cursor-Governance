---
name: plan
version: "2.0.0"
description: "Planning playbook — load permanent fixtures, draft execution-ready plan, auto-chain /ynp"
auto_chain: ynp
---

# /plan — Planning Playbook

> **Doctrine:** Proper planning prevents piss poor performance. A minute spent planning is an hour saved debugging.

## WHAT IT DOES

**Planning playbook** (not a bare template): Load permanent in-repo fixtures, fill plan section shells, harden the draft with the five-kernel pipeline, then hand off via `/ynp`.

Delegates to skill `l9-plan` v3:

- Load map: `skills/l9-plan/references/authority-bindings.md`
- Shells: `skills/l9-plan/references/plan-workflow.md`
- Kernels: `skills/l9-plan/references/kernel-pass-pipeline.md`

## STAGES

1. **Bind** target
2. **Load fixtures** (always + CHANGE + conditional per bindings)
3. **Gather** (doctrine: ask before build; lesson corpus)
4. **Draft shells** (path scopes, Constraints, Lock, dual DoD, TODOs, …)
5. **VALIDATE_PLAN**
6. **Kernel Pass Pipeline** on the **draft only**
7. **plan_status** + MSNA + handoff
8. **Auto-chain `/ynp`**

Planning-only — do **not** edit product/code files, commit, or push. Do **not** paste fixture bodies. Do **not** run GMP Phases 2–6 here.

## REQUIRED SHELLS (fail-closed)

1. Load log  
2. Planning Mode / plan_status / Objective  
3. Files in scope / Files out of scope  
4. Constraints (MUST / MUST NOT)  
5. Modification Lock (when CHANGE handoff)  
6. Pre-Validation  
7. Acceptance / Assumptions / ADRs  
8. TODO Plan (Phase-0 columns when CHANGE)  
9. Depth / Dependencies / waves / Critical path  
10. Unknown + Decision registers  
11. Validation matrix  
12. Plan Definition of Done + Post-implementation Definition of Done  
13. Milestones / Checkpoints / Checklist  
14. Kernel Pass Log  
15. Final Validation / MSNA / Handoff  

Full field shapes: `skills/l9-plan/references/plan-workflow.md`.

### Gate commands (governed workspaces)

```bash
make pr-check
# alias:
make pr
```

Make is case-sensitive: lowercase `pr-check` / `pr`.

## OUTPUT

See `plan-workflow.md` output format. Minimum skeleton:

```markdown
## PLAN: {title}

### Load log
| Fixture | Path | Status |
|---------|------|--------|
| … | … | Read |

### Planning Mode / plan_status / Objective
…

### Files in scope / Files out of scope
…

### Constraints / Modification Lock
…

### TODO / Dual DoD / Kernel Pass Log / MSNA / Handoff
…
```

→ **Auto-chains to /ynp**

--- End Command ---
