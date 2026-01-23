---
name: refactor-sweep
version: "1.0.0"
description: "Systematic refactoring across codebase"
auto_chain: gmp
---

# /refactor-sweep — Systematic Refactoring

## WHAT IT DOES

Apply refactoring pattern across codebase:

1. Find all instances
2. Generate TODO plan
3. Execute via /gmp
4. Verify completeness

---

## USAGE

```
/refactor-sweep "rename foo to bar"
/refactor-sweep "add timeout to all httpx calls"
/refactor-sweep "replace print with logger"
```

---

## EXECUTION

### 1. FIND INSTANCES

```bash
rg "{pattern}" --type py -l
```

### 2. GENERATE PLAN

| # | File | Line | Current | Target |
|---|------|------|---------|--------|
| 1 | a.py | 20 | foo() | bar() |
| 2 | b.py | 35 | foo() | bar() |

### 3. VALIDATE SCOPE

- Check no protected files
- Check test coverage exists
- Estimate impact

### 4. EXECUTE

Generate `/gmp` scope:

```markdown
## TODO PLAN
| T# | File | Lines | Action | Description |
|----|------|-------|--------|-------------|
| T1 | a.py | 20 | Replace | foo → bar |
```

---

## OUTPUT

```markdown
## 🔄 REFACTOR-SWEEP: {pattern}

### Instances Found: N
| File | Line | Match |
|------|------|-------|

### Plan
| # | File | Change |
|---|------|--------|

### Risk Assessment
**Files:** N
**Tests:** ✅ exist
**Protected:** None

⏸️ Ready for /gmp
```

→ **Auto-chains to /gmp**

--- End Command ---
