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
