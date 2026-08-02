---
name: plan
version: "1.2.0"
description: "Deep execution plan: doctrine, CCP fields, five-kernel pipeline, pre/final validation, milestones, checkpoints, checklist"
auto_chain: ynp
---

# /plan — Execution Planning

> **Doctrine:** Proper planning prevents piss poor performance. A minute spent planning is an hour saved debugging.

## WHAT IT DOES

Create a structured plan before implementation. Delegates template authority to skill `l9-plan` → `skills/l9-plan/references/plan-workflow.md` (SSOT).

1. Pre-Validate (mandatory; + lesson corpus when available)
2. Define objective + falsifiable success; Planning Mode
3. Identify inspection vs modification scope
4. List TODO items with depth + conditional sections
5. Map dependencies, waves, milestones, checkpoints
6. Unknown/Decision registers; Validation matrix
7. VALIDATE_PLAN then **five-kernel pipeline** on the draft ([kernel-pass-pipeline.md](../skills/l9-plan/references/kernel-pass-pipeline.md))
8. Kernel Pass Log + plan_status + MSNA + handoff
9. Final Validation (mandatory; `make pr-check` when code in scope)
10. Auto-chain to `/ynp`

Planning-only — do not edit product/code files, commit, or push from `/plan`. Kernel passes may rewrite the **plan draft only**.

Patterns: `skills/l9-plan/references/ccp-plan-patterns.md` (do not duplicate kernel paths here).

---

## EXECUTION

Follow skill `l9-plan`. Required sections (fail-closed if any missing):

1. Doctrine / Planning Mode / plan_status
2. Objective (+ Success)
3. Scope (inspection + modification; in/out)
4. Pre-Validation (+ lesson corpus)
5. TODO Plan (+ Depth + conditionals when triggered)
6. Dependencies / waves
7. Unknown + Decision registers
8. Validation matrix
9. Milestones / Checkpoints / Checklist
10. Risks / Estimate
11. Kernel Pass Log (five Applied/Blocked rows)
12. Final Validation
13. Minimum Safe Next Action + handoff profile

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

Thin mirror — full template is `skills/l9-plan/references/plan-workflow.md`.

```markdown
## PLAN: {title}

### Planning Mode
**Mode:** {Quick|Standard|Deep|Release} — {justification}

### plan_status
{Ready|ConditionallyReady|Partial|Blocked|Failed}

### Objective / Scope / Pre-Validation / TODOs / Depth / …
(see plan-workflow.md)

### Kernel Pass Log (mandatory)
| Kernel | Path | Status | Material deltas |
|--------|------|--------|-----------------|
| Improve | (see kernel-pass-pipeline.md) | Applied \| Blocked | … |
| … | … | … | … |

### Final Validation / MSNA / Handoff
…
```

→ **Auto-chains to /ynp** (recommends /gmp or /forge)

--- End Command ---
