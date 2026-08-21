---
name: Adapt Cursor GMP Integration Pack
overview: Re-align the Cursor GMP Integration Pack with L9's current state by removing Stage 2 (Intelition), fixing hardcoded paths, updating directory structure, and focusing on operational maturity stages (5-8) that complement existing GMP-48/49 work.
todos:
  - id: path-fixes
    content: Fix all hardcoded paths (/Users/ib-mac/ → $HOME) in all 6 pack files
    status: completed
  - id: stage2-removal
    content: Remove Stage 2 (Intelition) references from all pack files
    status: completed
  - id: directory-updates
    content: Update directory structure (core/agents/bootstrap/ → agents/cursor/)
    status: completed
  - id: stage-status
    content: Mark stages 1-4 as already done with GMP-48/49 references
    status: completed
  - id: tier-metadata
    content: Add tier classification (UX_TIER) to GMP prompts
    status: completed
  - id: stage-renumbering
    content: Renumber stages after Stage 2 removal (3→2, 4→3, etc.)
    status: completed
    dependencies:
      - stage2-removal
---

# GMP Plan: Adapt Cursor GMP Integrati

on Pack for L9 Current State

## Objective

Adapt the Cursor GMP Integration Pack (`docs/__Notes/consolidation.py/`) to align with L9's current architecture, removing redundant stages and focusing on operational maturity that complements existing GMP-48/49 work.

## Variable Bindings

```yaml
TASK_NAME: adapt_cursor_gmp_integration_pack
EXECUTION_SCOPE: >
  Re-align Cursor GMP Integration Pack by:
    1. Removing Stage 2 (Intelition - component doesn't exist)
    2. Fixing hardcoded paths (/Users/ib-mac/ → $HOME)
    3. Updating directory structure (core/agents/bootstrap/ → agents/cursor/)
    4. Marking stages 1-4 as "already done" (covered by GMP-48/49)
    5. Adapting stages 5-8 for operational maturity
SPEC_PATH: docs/__Notes/consolidation.py/
RISK_LEVEL: Low
IMPACT_METRICS: Documentation accuracy, pack usability, operational maturity
VALIDATION_NOTES: Verify all paths fixed, Stage 2 removed, directory structure updated
```



## Phase 0: TODO Plan Lock

### Phase 1: Path Fixes (Automated)

- **[T1]** File: `docs/__Notes/consolidation.py/README-CURSOR-GMP-PACK-v1.0.md`
- Lines: All

- Action: Replace

- Target: Hardcoded paths

- Change: Replace `/Users/ib-mac/Projects/L9` with `$HOME/Projects/L9` (or relative paths)

- Gate: None

- **[T2]** File: `docs/__Notes/consolidation.py/GMP-Cursor-Master-v1.0.md`
- Lines: All

- Action: Replace
- Target: Hardcoded paths

- Change: Replace `/Users/ib-mac/Projects/L9` with `$HOME/Projects/L9`
- Gate: None

- **[T3]** File: `docs/__Notes/consolidation.py/GMP-Cursor-Stage-1-v1.0.md`
- Lines: All

- Action: Replace

- Target: Hardcoded paths

- Change: Replace `/Users/ib-mac/Projects/L9` with `$HOME/Projects/L9`

- Gate: None

- **[T4]** File: `docs/__Notes/consolidation.py/GMP-Cursor-Stages-2-8-v1.0.md`
- Lines: All
- Action: Replace

- Target: Hardcoded paths

- Change: Replace `/Users/ib-mac/Projects/L9` with `$HOME/Projects/L9`
- Gate: None

- **[T5]** File: `docs/__Notes/consolidation.py/CURSOR-INTEGRATION-RUNBOOK-v1.0.md`
- Lines: All

- Action: Replace

- Target: Hardcoded paths

- Change: Replace `/Users/ib-mac/Projects/L9` with `$HOME/Projects/L9`
- Gate: None

- **[T6]** File: `docs/__Notes/consolidation.py/DELIVERY-SUMMARY.md`
- Lines: All
- Action: Replace

- Target: Hardcoded paths

- Change: Replace `/Users/ib-mac/Projects/L9` with `$HOME/Projects/L9`
- Gate: None

### Phase 2: Stage 2 Removal (Intelition)

- **[T7]** File: `docs/__Notes/consolidation.py/README-CURSOR-GMP-PACK-v1.0.md`
- Lines: 48, 77, 98, 127, 205

- Action: Replace

- Target: Stage 2 references

- Change: Remove or mark Stage 2 as "REMOVED - Intelition component doesn't exist in L9"

- Gate: None

- **[T8]** File: `docs/__Notes/consolidation.py/GMP-Cursor-Master-v1.0.md`

- Lines: 100-169 (Stage 2 section)
- Action: Delete or Replace

- Target: Stage 2 section

- Change: Remove Stage 2 section entirely, update stage numbering (3→2, 4→3, etc.)

- Gate: None

- **[T9]** File: `docs/__Notes/consolidation.py/CURSOR-INTEGRATION-RUNBOOK-v1.0.md`

- Lines: 100-169 (Stage 2 section)

- Action: Delete or Replace
- Target: Stage 2 section

- Change: Remove Stage 2 section, update subsequent stage numbers
- Gate: None

- **[T10]** File: `docs/__Notes/consolidation.py/DELIVERY-SUMMARY.md`

- Lines: 53, 123, 141-144, 168

- Action: Replace

- Target: Stage 2 references

- Change: Remove Stage 2 from tables and descriptions
- Gate: None

### Phase 3: Directory Structure Updates

- **[T11]** File: `docs/__Notes/consolidation.py/GMP-Cursor-Stages-2-8-v1.0.md`
- Lines: 11, 16

- Action: Replace

- Target: Directory paths

- Change: Replace `core/agents/bootstrap/` with `agents/cursor/`, `core/agents/registry.py` with `core/agents/registry.py` (verify exists), `core/agents/executor.py` with `core/agents/executor.py` (verify exists)
- Gate: None

- **[T12]** File: `docs/__Notes/consolidation.py/GMP-Cursor-Master-v1.0.md`

- Lines: 65
- Action: Replace

- Target: Directory paths

- Change: Replace `core/agents/bootstrap/` with `agents/cursor/`

- Gate: None

- **[T13]** File: `docs/__Notes/consolidation.py/CURSOR-INTEGRATION-RUNBOOK-v1.0.md`

- Lines: 107, 108, 145, 181, 394, 425
- Action: Replace
- Target: Directory paths

- Change: Replace `core/agents/bootstrap/` references with `agents/cursor/` where appropriate
- Gate: None

### Phase 4: Stage Status Updates (Mark 1-4 as Already Done)

- **[T14]** File: `docs/__Notes/consolidation.py/README-CURSOR-GMP-PACK-v1.0.md`

- Lines: 72-84 (8 Stages table)

- Action: Replace

- Target: Stage status

- Change: Mark stages 1-4 as "✓ Already Done (GMP-48/49)" with note referencing reports
- Gate: None

- **[T15]** File: `docs/__Notes/consolidation.py/GMP-Cursor-Master-v1.0.md`

- Lines: 28-99 (Stage 1-4 sections)
- Action: Wrap

- Target: Stage descriptions

- Change: Add note at top of each stage: "NOTE: This stage was completed in GMP-48/49. See reports/GMP_Report_GMP-48-*.md and GMP_Report_GMP-49-*.md"
- Gate: None

### Phase 5: Add Tier Metadata

- **[T16]** File: `docs/__Notes/consolidation.py/GMP-Cursor-Master-v1.0.md`
- Lines: 1-10 (header)
- Action: Insert

- Target: YAML frontmatter

- Change: Add tier classification: `tier: UX_TIER` (documentation)

- Gate: None

- **[T17]** File: `docs/__Notes/consolidation.py/GMP-Cursor-Stage-1-v1.0.md`

- Lines: 1-10 (header)
- Action: Insert

- Target: YAML frontmatter

- Change: Add tier classification: `tier: UX_TIER`
- Gate: None

### Phase 6: Update Stage Numbering (After Stage 2 Removal)

- **[T18]** File: `docs/__Notes/consolidation.py/README-CURSOR-GMP-PACK-v1.0.md`

- Lines: 46-54, 72-84

- Action: Replace

- Target: Stage numbers

- Change: Renumber stages: 3→2, 4→3, 5→4, 6→5, 7→6, 8→7 (7 stages total)

- Gate: None

- **[T19]** File: `docs/__Notes/consolidation.py/GMP-Cursor-Master-v1.0.md`

- Lines: All stage references
- Action: Replace
- Target: Stage numbers

- Change: Renumber all stages after Stage 2 removal
- Gate: None

- **[T20]** File: `docs/__Notes/consolidation.py/CURSOR-INTEGRATION-RUNBOOK-v1.0.md`
- Lines: All stage references

- Action: Replace

- Target: Stage numbers

- Change: Renumber all stages after Stage 2 removal

- Gate: None

## Files to Modify

1. `docs/__Notes/consolidation.py/README-CURSOR-GMP-PACK-v1.0.md`

2. `docs/__Notes/consolidation.py/GMP-Cursor-Master-v1.0.md`

3. `docs/__Notes/consolidation.py/GMP-Cursor-Stage-1-v1.0.md`
4. `docs/__Notes/consolidation.py/GMP-Cursor-Stages-2-8-v1.0.md`

5. `docs/__Notes/consolidation.py/CURSOR-INTEGRATION-RUNBOOK-v1.0.md`

6. `docs/__Notes/consolidation.py/DELIVERY-SUMMARY.md`

## Constraints

- **KERNEL-TIER files NOT in scope:** No changes to executor, kernel_loader, etc.

- **No duplicated responsibilities:** Pack is documentation only, no code changes

- **Unified interfaces:** N/A (documentation files)
- **No placeholders:** All changes are concrete replacements

- **Surgical edits only:** Use search_replace for all changes

## Validation Gates

- [ ] All `/Users/ib-mac/` paths replaced

- [ ] All Stage 2 references removed

- [ ] All `core/agents/bootstrap/` updated to `agents/cursor/` where appropriate
- [ ] Stage numbering updated consistently

- [ ] Files compile/validate (markdown syntax check)

## Expected Outcome

- Pack adapted to current L9 state

- Stage 2 (Intelition) completely removed

- All paths use `$HOME` convention

- Directory structure aligned with `agents/cursor/`

- Stages 1-4 marked as "already done" with GMP-48/49 references

- Stages 5-8 (now 4-7) ready for execution focusing on operational maturity