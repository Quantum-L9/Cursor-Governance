---
name: extract_align
version: "1.0.0"
description: "Extract patterns and align with standards"
auto_chain: ynp
---

# /extract_align — Pattern Extraction & Alignment

## WHAT IT DOES

1. Extract patterns from code (and from skill/prompt/workflow packs when those are the target)
2. Compare to L9 standards
3. Identify misalignments
4. Generate alignment plan

Load `skills/l9-code-analysis/references/pattern-alignment.md` for scan dimensions.

---

## EXECUTION

### 1. EXTRACT PATTERNS

```
SCAN:
├── Error handling patterns
├── Logging patterns
├── Async patterns
├── Import patterns
├── Testing patterns
└── Pack / workflow (when target is a skill, prompt, or workflow pack)
    ├── Repeated node or section structures
    ├── Reasoning chains (if → validate → mutate → return)
    └── Reusable field / ID patterns grounded in repo docs
```

### 2. COMPARE TO STANDARDS

| Pattern | Found | L9 Standard | Aligned? |
|---------|-------|-------------|----------|
| Logging | print() | structlog | ❌ |
| HTTP | requests | httpx | ❌ |
| Async | sync I/O | async def | ❌ |

### 3. ALIGNMENT PLAN

| # | Current | Target | Files |
|---|---------|--------|-------|
| 1 | print() | logger.info() | N files |

---

## OUTPUT

```markdown
## 🎯 EXTRACT_ALIGN: {scope}

### Patterns Found
| Pattern | Count | Standard |
|---------|-------|----------|

### Misalignments
| Issue | Files | Fix |
|-------|-------|-----|

### Alignment Plan
| # | Change | Scope |
|---|--------|-------|

→ /refactor-sweep to execute
```

→ **Auto-chains to /ynp**

--- End Command ---
