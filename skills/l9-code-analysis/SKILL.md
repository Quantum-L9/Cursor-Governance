---
name: l9-code-analysis
description: Rapidly analyze, deeply evaluate, or combine analysis and evaluation for code targets. Use when exploring unfamiliar code, auditing structure, mapping flows, identifying hotspots, or assessing quality before edits.
---

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

---

<!-- migrated-from: evaluate.md -->

---
name: evaluate
version: "7.0.0"
description: "Deep evaluation — compliance, health, gaps, actionable TODOs"
auto_chain: ynp
---

# /evaluate — Deep Evaluation

## WHAT IT DOES

Comprehensive audit across 6 dimensions → actionable GMP TODOs:

1. **Workflow State** — Phase, TODOs, blockers
2. **Tier Health** — KERNEL/RUNTIME/INFRA/UX compliance
3. **GMP Compliance** — Phase gates, missing steps
4. **Code Quality** — L9 patterns, anti-patterns
5. **Dependencies** — Imports, circular refs, orphans
6. **Gaps** — What's missing vs production-ready

---

## EXECUTION

### 1. STATE_SYNC

```
Read workflow_state.md:
- Current PHASE (0-6)
- Active TODOs
- Priority queue (🔴/🟠/🟡/🔵)
```

### 2. TIER CLASSIFICATION

| Tier | Rigor |
|------|-------|
| KERNEL | FULL — every function traced |
| RUNTIME | HIGH — public APIs + error paths |
| INFRA | DEPLOYMENT — wiring + env vars |
| UX | STANDARD — structure + tests |

### 3. L9 HEALTH CHECKS

| Check | Required |
|-------|----------|
| structlog | Not logging/print |
| httpx | Not requests/aiohttp |
| async I/O | Async def for I/O |
| pydantic v2 | model_config, not Config |
| packet logging | Critical ops → PacketEnvelope |
| error handling | try/except + recovery |
| timeouts | External calls have timeout |

### 4. ANTI-PATTERNS

| Pattern | Severity |
|---------|----------|
| Bare except | 🔴 |
| sync in async | 🔴 |
| global state | 🟠 |
| missing types | 🟡 |
| no docstring | 🟡 |

### 5. GAP ANALYSIS

```
Production-ready requires:
├── All L9 patterns ✅
├── No anti-patterns
├── Tests exist + pass
├── Docs complete
└── GMP phases 0-6 done
```

---

## OUTPUT FORMAT

```markdown
## 📊 EVALUATE: {target}

**Tier:** {tier}
**Health Score:** {0-100}%

### L9 Compliance
| Pattern | Status | Location |
|---------|--------|----------|

### Anti-Patterns
| Issue | Severity | File:Line |
|-------|----------|-----------|

### Gaps
| Gap | Priority | Fix |
|-----|----------|-----|

### GMP TODOs (Batched)
| # | Scope | Files | Priority |
|---|-------|-------|----------|
```

→ **Auto-chains to /ynp**

--- End Command ---

---

<!-- migrated-from: analyze_evaluate.md -->

---
name: analyze_evaluate
version: "7.0.0"
description: "Combined analysis + evaluation in one pass"
auto_chain: ynp
---

# /analyze+evaluate — Combined Deep Analysis

## WHAT IT DOES

Combines `/analyze` + `/evaluate` with cross-referencing:

| Capability | Description |
|------------|-------------|
| Cross-Reference | Structure issues → compliance gaps |
| Deduplication | One finding per problem |
| Impact Projection | Fix X → unblocks Y |
| Tech Debt Score | Unified metric |
| Auto-Fix Candidates | Quick wins flagged |

---

## EXECUTION

### 1. CLASSIFY TARGET

```
MODULE | SERVICE | AGENT | ROUTER | TOOL | KERNEL | CONFIG
```

### 2. PARALLEL ANALYSIS

```
ANALYZE → Structure, Flows, Hotspots, Dependencies
    ↓ cross-reference
EVALUATE → Patterns, Compliance, Gaps
    ↓ synthesize
COMBINED → Cross-findings, Impact, Tech Debt, Auto-Fix
```

### 3. IMPACT SCORING

```
Impact = (downstream_blocked × 2) + upstream_unlocked + cross_impact
```

### 4. AUTO-FIX CATEGORIES

| Category | Time | Examples |
|----------|------|----------|
| 🤖 AUTO | <1min | imports, formatting, bare except |
| 🔧 SEMI | 1-5min | docstrings, timeouts, packet logging |
| 👤 MANUAL | >5min | refactoring, architecture |

---

## OUTPUT FORMAT

```markdown
## 🔍 ANALYZE+EVALUATE: {target}

### Summary
| Metric | Score |
|--------|-------|
| Structure | N% |
| Quality | N% |
| Compliance | N% |
| Tech Debt | N% |

### Cross-Referenced Findings
| # | Structure + Compliance = Finding | Impact |
|---|----------------------------------|--------|

### Impact Projection
| Fix | Unblocks | Score |
|-----|----------|-------|

### Auto-Fix Candidates
🤖 {automatable}
🔧 {semi-auto}
👤 {manual}

### Prioritized TODOs
| # | TODO | Files | Impact | Auto? |
|---|------|-------|--------|-------|
```

→ **Auto-chains to /ynp**

--- End Command ---
