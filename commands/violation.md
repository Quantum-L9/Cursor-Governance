---
name: violation
version: "1.1.0"
description: "Report governance violation"
before_chain: rules
auto_chain: ynp
---

# /violation — Report Violation

## WHAT IT DOES

Report and track governance violations.

---

## VIOLATION TYPES

| Type | Severity | Example |
|------|----------|---------|
| Protected file modified | 🔴 | executor.py changed without approval |
| GMP skipped | 🟠 | No Phase 0 plan |
| Anti-pattern | 🟡 | Bare except |
| Missing test | 🟡 | No test for new function |

---

## REPORT FORMAT

```markdown
## ⚠️ VIOLATION REPORT

**Type:** {type}
**Severity:** 🔴/🟠/🟡
**Location:** {file:line}
**Description:** {what happened}

### Evidence
{code or diff}

### Required Action
{fix}

### Prevention
{how to avoid}
```

---

## TRACKING

Violations logged to:
- Memory (via /mem write)
- workflow_state.md (open questions)

---

## OUTPUT

```markdown
## ⚠️ VIOLATION: {type}

**File:** {path}
**Severity:** {level}

### Issue
{description}

### Fix
{action}

### Logged
- Memory ✅
- workflow_state.md ✅
```

--- End Command ---
