# Global rules corpus audit

Generated: `2026-08-02T14:10:48Z`

## Summary

- Total rules: **58**
- Always rules: **38**
- Derived compatibility IDs: **50**
- Rules over 300 lines: **4**
- Deprecated rules: **1**

## Leverage-ranked findings

### RCA-005 - High-cost rules are marked Always

**Priority:** 67
**Severity:** 4/5
**Confidence:** confirmed

**Evidence:** 60-anti-patterns.mdc, 92-learned-lessons.mdc, 99-incident-report.mdc

**Impact:** Maximum activation cost is paid on every task.

**Action:** Convert to Agent Requested, Auto Attached, or an explicit skill after behavioral review.

### RCA-001 - Always activation footprint requires per-rule justification

**Priority:** 61
**Severity:** 3/5
**Confidence:** confirmed

**Evidence:** 38 of 58 rules (66%) resolve to always activation.

**Impact:** Broad persistent context can create instruction collisions and consume agent context.

**Action:** Review each Always rule; keep only short non-negotiable governance and irreversible-action constraints.

### RCA-004 - Rules exceed the 500-line hard target

**Priority:** 59
**Severity:** 4/5
**Confidence:** confirmed

**Evidence:** 92-learned-lessons.mdc (778 lines)

**Impact:** Very large rule payloads raise context and contradiction risk.

**Action:** Split immediately behind stable IDs and preserve compatibility aliases where required.

### RCA-003 - Oversized active rules should be split or converted to procedures

**Priority:** 49
**Severity:** 3/5
**Confidence:** confirmed

**Evidence:** 03-mcp-memory.mdc (419 lines), 60-anti-patterns.mdc (351 lines), 92-learned-lessons.mdc (778 lines), 99-incident-report.mdc (463 lines)

**Impact:** Large rules are expensive to attach and harder to keep internally consistent.

**Action:** Move multi-step procedures to skills/commands and keep persistent rule contracts focused.

### RCA-002 - Most legacy rules still use derived compatibility IDs

**Priority:** 46
**Severity:** 2/5
**Confidence:** confirmed

**Evidence:** 50 rules lack an explicit immutable frontmatter ID.

**Impact:** Renames cannot be distinguished reliably from replacement or deletion.

**Action:** Add explicit IDs when rules are materially edited; do not mass-rewrite solely for metadata.

### RCA-006 - Deprecated rules remain in the active rule directory

**Priority:** 39
**Severity:** 2/5
**Confidence:** confirmed

**Evidence:** 03-mcp-memory.mdc

**Impact:** Compatibility content can still be discovered or explicitly referenced.

**Action:** Retain only with a documented compatibility reason and removal plan.

## Convergence

Scope, activation, size, identity, deprecation, and adversarial passes completed. Findings stabilized.
No mass conversion was performed without behavioral evidence.
