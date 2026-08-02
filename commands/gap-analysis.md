---
name: gap-analysis
version: "1.1.0"
description: "Identify gaps vs target state"
before_chain: rules
auto_chain: ynp
---

# /gap-analysis — Gap Identification

## WHAT IT DOES

Compare current state vs target → identify gaps.

---

## EXECUTION

### 1. DEFINE TARGET

```
TARGET STATE:
├── All L9 patterns
├── No anti-patterns
├── Tests exist
├── Docs complete
├── GMP phases done
```

### 2. ASSESS CURRENT

| Dimension | Current | Target | Gap |
|-----------|---------|--------|-----|
| Patterns | 80% | 100% | 20% |
| Tests | 60% | 100% | 40% |
| Docs | 50% | 100% | 50% |

### 3. PRIORITIZE GAPS

| Priority | Gap | Impact | Effort |
|----------|-----|--------|--------|
| 🔴 | Missing tests | High | Medium |
| 🟠 | Anti-patterns | Medium | Low |

---

## OUTPUT

```markdown
## 📊 GAP ANALYSIS: {scope}

### Current vs Target
| Dimension | Current | Target | Gap |
|-----------|---------|--------|-----|

### Gaps (Prioritized)
| # | Gap | Priority | Fix |
|---|-----|----------|-----|

### Effort Estimate
**Total gaps:** N
**Effort:** {estimate}

### Recommended GMPs
| GMP | Scope | Gaps Addressed |
|-----|-------|----------------|
```

→ **Auto-chains to /ynp**

--- End Command ---
