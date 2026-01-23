---
name: confirm-wiring
version: "1.0.0"
description: "Verify component is fully wired — no orphan refs"
auto_chain: ynp
---

# /confirm-wiring — Integration Audit

## WHAT IT DOES

Verify a component is fully wired:

1. All imports resolve
2. All exports consumed
3. All tests exist
4. No orphan references

---

## EXECUTION

### 1. VERIFY IMPORTS

```bash
python3 -c "from {package} import {component}"
```

### 2. VERIFY EXPORTS

Check `__init__.py` exports match usage.

### 3. VERIFY CONSUMERS

```bash
rg "from.*{component}|import.*{component}" --type py -l
```

### 4. VERIFY TESTS

```bash
ls tests/{package}/test_{component}.py
pytest tests/{package}/test_{component}.py -v
```

---

## OUTPUT

```markdown
## ✅ WIRING CONFIRMED: {component}

| Check | Status |
|-------|--------|
| Imports resolve | ✅ |
| Exports consumed | ✅ |
| Tests exist | ✅ |
| Tests pass | ✅ |

**Consumers:** {list}
**Orphans:** None
```

OR

```markdown
## ❌ WIRING INCOMPLETE: {component}

| Issue | Location | Fix |
|-------|----------|-----|
| Missing import | file.py:10 | Add import |
| No test | — | Create test |

→ Run /wire to fix
```

--- End Command ---
