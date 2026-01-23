---
name: clean_compress
version: "1.0.0"
description: "Clean and compress code/files"
auto_chain: ynp
---

# /clean_compress — Code Cleanup

## WHAT IT DOES

Clean and compress code:

1. Remove dead code
2. Remove unused imports
3. Compress verbose patterns
4. Standardize formatting

---

## EXECUTION

### 1. FIND DEAD CODE

```bash
vulture . --min-confidence 80
```

### 2. FIND UNUSED IMPORTS

```bash
ruff check --select F401 .
```

### 3. AUTO-FIX

```bash
ruff check --fix .
```

### 4. FORMAT

```bash
ruff format .
```

---

## CLEANUP TARGETS

| Target | Tool |
|--------|------|
| Dead code | vulture |
| Unused imports | ruff F401 |
| Formatting | ruff format |
| Type stubs | ruff |

---

## OUTPUT

```markdown
## 🧹 CLEANUP: {scope}

### Found
| Issue | Count |
|-------|-------|
| Dead code | N |
| Unused imports | N |
| Format issues | N |

### Fixed
| Fix | Files |
|-----|-------|
| Imports removed | N |
| Formatted | N |

### Remaining (manual)
| Issue | Location |
|-------|----------|
```

→ **Auto-chains to /ynp**

--- End Command ---
