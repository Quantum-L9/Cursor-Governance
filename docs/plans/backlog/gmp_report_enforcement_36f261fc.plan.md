---
name: GMP Report Enforcement
overview: Modify GMP protocol to make report generation MANDATORY (not optional) and add enforcement gates that block /ynp auto-chain until script is executed and workflow_state.md is updated.
todos:
  - id: edit-gmp-cmd
    content: "Edit gmp.md: Remove 'optional/on-demand' language, add FINALIZATION GATE section"
    status: in_progress
  - id: edit-audit-rule
    content: "Edit 81-gmp-audit.mdc: Add enforcement rule making script execution mandatory"
    status: pending
  - id: edit-lessons
    content: "Edit 92-learned-lessons.mdc: Add lesson about CONFIRM not ending obligations"
    status: pending
  - id: verify-flow
    content: "Verify: Run small GMP to test new enforcement flow"
    status: pending
---

# GMP Report Generation Enforcement

## Problem Statement

GMP reports are frequently skipped because:

1. `gmp.md` labels script report as "On-Demand ONLY" and "Optional"
2. No hard gate exists between Phase 6 and `/ynp` auto-chain
3. The CONFIRM step creates cognitive context switch that loses report obligation

## Solution: Mandatory Script Gate

### File 1: [.cursor-commands/commands/gmp.md](.cursor-commands/commands/gmp.md)

**Changes:**

1. **Line 21**: Change chain from:
   ```
   /gmp → Phase 0-6 → INLINE REPORT → [Optional] Script Report → workflow_state.md → /ynp
   ```


To:

   ```
   /gmp → Phase 0-6 → INLINE REPORT → SCRIPT EXECUTION (MANDATORY) → workflow_state.md → /ynp
   ```

2. **Lines 49-50**: Change script table "When" column:

   - From: `On-demand (Phase 6)`
   - To: `MANDATORY (Phase 6 completion)`

3. **Line 96**: Change phase table:

   - From: `generate_gmp_report.py (on-demand)`
   - To: `generate_gmp_report.py (MANDATORY)`

4. **Lines 184-197**: Replace "SCRIPT REPORT (Phase 6 - On-Demand)" section with:
````markdown
## SCRIPT REPORT (Phase 6 - MANDATORY)

**MUST execute before /ynp auto-chain:**

```bash
python3 scripts/workflow/generate_gmp_report.py \
  --task "{task description}" \
  --tier {TIER} \
  --todo "file|lines|action|desc" \
  --validation "py_compile|✅,ruff|✅,tests|✅" \
  --update-workflow
````


**GATE:** /ynp BLOCKED until script executed

````

5. **Add new section after line 208** - FINALIZATION GATE:

```markdown
## FINALIZATION GATE (Before /ynp)

Before auto-chaining to /ynp, verify:

| Check | Required |
|-------|----------|
| Script executed | generate_gmp_report.py ran |
| Report file exists | reports/GMP-Report-{N}-*.md |
| workflow_state.md updated | --update-workflow flag used |

**If ANY check fails:** DO NOT chain to /ynp. Complete missing steps first.
````

### File 2: [.cursor/rules/81-gmp-audit.mdc](.cursor/rules/81-gmp-audit.mdc)

**Add to "GMP report generation protocol" section:**

```markdown
### ENFORCEMENT: Script Execution is NOT Optional

**Effective: 2026-01-25**

After ANY GMP execution (Phase 6 complete), you MUST:

1. Run `generate_gmp_report.py` with `--update-workflow` flag
2. Verify report file created in `reports/`
3. Verify workflow_state.md updated

**BLOCKED:** Cannot auto-chain to /ynp until all three are verified.

**Rationale:** "Optional" language caused repeated report omission. This is now a hard gate.
```

### File 3: [.cursor/rules/92-learned-lessons.mdc](.cursor/rules/92-learned-lessons.mdc)

**Add new lesson:**

```markdown
## 🔴 CRITICAL: GMP Reports are MANDATORY

### Never Skip Report Generation After GMP

**Effective: 2026-01-25**

After completing ANY GMP (Phase 6):
- **MUST** run `generate_gmp_report.py --update-workflow`
- **MUST** verify report file exists before /ynp
- **MUST** verify workflow_state.md was updated

**The CONFIRM step does NOT end your obligations.** After user confirms, you still owe:
1. Phase 1-6 execution
2. Script report generation
3. workflow_state.md update
4. THEN /ynp

**Lesson:** 2026-01-25 — Reports repeatedly skipped because protocol said "optional". Now mandatory.
```

## Execution Order

1. Edit `gmp.md` - Remove optional language, add FINALIZATION GATE
2. Edit `81-gmp-audit.mdc` - Add enforcement rule
3. Edit `92-learned-lessons.mdc` - Add learned lesson for persistence
4. Test by running a small GMP to verify enforcement
