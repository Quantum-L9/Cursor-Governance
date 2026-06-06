---
name: analysis-pattern-extract
description: 🎯 Pattern Extraction Tool
disable-model-invocation: true
---

---
command: PATTERN_EXTRACT
version: 1.0.0
category: analysis
tags: [learning, patterns, methodology, improvement]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: <1min
---

# 🎯 Pattern Extraction Tool

## 📖 Purpose
Extract successful patterns from conversation history and past solutions for replication and learning.

## 🎪 When to Use
- After completing successful complex task
- Want to replicate methodology
- Creating templates or standards
- Learning from past successes
- Building automation patterns

## 🚀 Execution

Reviews conversation history and extracts:
- Successful problem-solving approaches
- Effective command sequences
- Formatting requirements that worked
- Quality standards that produced results
- Methodologies to replicate

Creates consolidated guide capturing exact patterns for future use.

---

*Command Standard Version: 2.0.0*

---

<!-- migrated-from: commands/extract_align.md -->

---
name: extract_align
version: "1.0.0"
description: "Extract patterns and align with standards"
auto_chain: ynp
---

# /extract_align — Pattern Extraction & Alignment

## WHAT IT DOES

1. Extract patterns from code
2. Compare to L9 standards
3. Identify misalignments
4. Generate alignment plan

---

## EXECUTION

### 1. EXTRACT PATTERNS

```
SCAN:
├── Error handling patterns
├── Logging patterns
├── Async patterns
├── Import patterns
└── Testing patterns
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

