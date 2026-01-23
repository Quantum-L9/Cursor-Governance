---
name: analyze
version: "7.0.0"
description: "Rapid exploration — understand structure, map flows, identify hotspots"
auto_chain: ynp
---

# /analyze — Rapid Exploration

## WHAT IT DOES

Fast exploration to understand code before acting (~30 seconds):

1. **Orientation** — What is this? What does it do?
2. **Structure Map** — Files, classes, functions
3. **Flow Trace** — How data/control flows
4. **Hotspots** — Critical paths, complexity
5. **Quick Health** — Surface issues

**Chain:** `/analyze` → understand → `/evaluate` → audit → `/gmp` → fix

---

## /analyze vs /evaluate

| Aspect | /analyze | /evaluate |
|--------|----------|-----------|
| Goal | Understand | Audit |
| Speed | Fast (30s) | Thorough (2-5min) |
| Depth | Surface | Deep |
| Output | Structure map | Compliance report |

---

## EXECUTION

### 1. CLASSIFY TARGET

```
TYPES:
├── MODULE: Python package
├── SERVICE: Class with methods
├── AGENT: BaseAgent subclass
├── ROUTER: FastAPI routes
├── TOOL: Tool definition
├── KERNEL: YAML kernel
└── CONFIG: Settings, compose
```

### 2. STRUCTURE MAP

```markdown
{target}/
├── __init__.py (exports: X, Y)
├── models.py (3 classes)
├── service.py ← 🎯 HOTSPOT
└── tests/ (coverage: N%)
```

### 3. FLOW TRACE

```
Entry → Handler → Service → Storage
          ↓
     Governance.check()
```

### 4. HOTSPOT TABLE

| File | Complexity | Why Hot |
|------|------------|---------|
| service.py | HIGH | Main logic, many branches |

### 5. QUICK HEALTH

| Check | Status |
|-------|--------|
| structlog | ✅/❌ |
| async I/O | ✅/❌ |
| type hints | ✅/❌ |
| tests exist | ✅/❌ |

---

## OUTPUT FORMAT

```markdown
## 🔍 ANALYZE: {target}

**Type:** {MODULE/SERVICE/etc.}
**Tier:** {KERNEL/RUNTIME/INFRA/UX}

### Structure
{tree}

### Flows
{diagram}

### Hotspots
{table}

### Quick Health
{checklist}

### Recommendation
→ /evaluate (if needs deep audit)
→ /gmp (if issues found)
→ Continue (if healthy)
```

→ **Auto-chains to /ynp**

--- End Command ---
