---
name: wire
version: "10.0.0"
description: "Wire component — discover refs, fix broken, add missing"
auto_chain: ynp
---

# /wire — Component Wiring

## USAGE

```
/wire path/to/component.py
/wire ModuleName
```

## CHAIN

```
/wire → DISCOVERY → ANALYSIS → PLAN → EXECUTE → VALIDATE → REPORT
```

---

## PHASES

### 1. DISCOVERY

Find ALL references to component:

```bash
rg "component_name" --type py -l
rg "from.*component|import.*component" --type py
```

Output:
| File | Line | Type | Status |
|------|------|------|--------|
| service.py | 8 | Import | ✅/❌ |

### 2. ANALYSIS

| Component Type | Check |
|----------------|-------|
| Config (.yaml) | Loader exists, path correct |
| Module (.py) | __init__.py exports, consumers import |
| Service/Class | Instantiation, registration, tests |
| Route | __init__.py export, server.py registered |

### 3. PLAN

| # | Action | File | Change |
|---|--------|------|--------|
| W1 | Fix path | service.py:8 | old → new |
| W2 | Add import | loader.py:1 | from X import Y |
| W3 | Add export | __init__.py | from .module import Class |

### 4. EXECUTE

- One edit per action
- Surgical only (StrReplace, not rewrite)
- Preserve formatting

### 5. VALIDATE

```bash
python3 -m py_compile {files}
python3 -c "from {package} import {component}"
pytest tests/{package}/ -v
```

### 6. VERIFY (Recursive)

Re-run discovery → confirm all refs fixed, no new broken refs.

---

## OUTPUT

```markdown
## 🔌 WIRE: {component}

| Metric | Value |
|--------|-------|
| Refs found | N |
| Fixed | N |
| Added | N |

### Actions
| # | Action | Status |
|---|--------|--------|
| W1 | ... | ✅ |

### Validation
| Check | Status |
|-------|--------|
| py_compile | ✅ |
| imports | ✅ |
| tests | ✅ |
```

---

## PROTECTED FILES

If wiring requires changes to protected files → STOP → route to `/gmp`:
- `core/agents/executor.py`
- `runtime/websocket_orchestrator.py`
- `memory/substrate_service.py`
- `docker-compose.yml`

--- End Command ---
