---
name: consolidate
version: "1.0.0"
description: "Consolidate scattered code/files"
auto_chain: ynp
---

# /consolidate — Code Consolidation

## WHAT IT DOES

Consolidate scattered implementations:

1. Find duplicates
2. Identify common patterns
3. Extract to shared module
4. Update references

---

## EXECUTION

### 1. FIND DUPLICATES

```bash
# Find similar code
rg "{pattern}" --type py -l
```

### 2. ANALYZE

| File | Implementation | Lines |
|------|----------------|-------|
| a.py | version 1 | 20-40 |
| b.py | version 2 | 30-50 |

### 3. CONSOLIDATE

```markdown
## Consolidation Plan

**Target:** shared/{module}.py
**Source Files:** {list}
**Action:** Extract common code

| # | From | To | Lines |
|---|------|-----|-------|
| 1 | a.py:20-40 | shared/module.py | new |
| 2 | b.py:30-50 | import from shared | replace |
```

### 4. EXECUTE

Via `/gmp`:
- Create shared module
- Update imports
- Remove duplicates
- Add tests

---

## OUTPUT

```markdown
## 📦 CONSOLIDATE: {pattern}

### Duplicates Found
| File | Lines | Similarity |
|------|-------|------------|

### Plan
**Consolidate to:** {target}
**Files affected:** {count}

### TODO (for /gmp)
| # | Action | File |
|---|--------|------|
```

→ **Auto-chains to /ynp**

--- End Command ---
