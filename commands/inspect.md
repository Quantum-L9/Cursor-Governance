name: inspect
version: "1.0.0"
description: "Unified first-touch inspection — understand, evaluate, and route components deterministically"
auto_chain: ynp

# /inspect — Unified Analysis + Evaluation + Routing

NON-NEGOTIABLE
- READ-ONLY
- NO code modification
- NO fixes
- NO wiring
- NO harvesting
- This command DECIDES, it does NOT ACT

---

PURPOSE

Provide a single, deterministic entry point to:

1. Understand a component
2. Evaluate its health and compliance
3. Quantify impact and risk
4. Decide the correct NEXT command
5. STOP

This replaces:
/analyze
/evaluate
/analyze+evaluate

---

USAGE

/inspect path/to/file.py
/inspect ModuleName
/inspect ServiceName

---

POSITION IN TOOLCHAIN

UNKNOWN COMPONENT
 ↓
/inspect          ← YOU ARE HERE
 ↓
Decision
 ├─ Harvestable → /harvest-analyze
 ├─ Mechanical change → /refactor-sweep
 ├─ Structural wiring → /wire
 ├─ Semantic / lifecycle → /gmp
 └─ Healthy → STOP

---

CHAIN

/inspect
→ CLASSIFY
→ ORIENT
→ STRUCTURE + FLOW
→ COMPLIANCE + HEALTH
→ IMPACT SCORING
→ ROUTING DECISION
→ REPORT
→ STOP

---

PHASE 1 — CLASSIFY (WHAT IS THIS?)

Classify the target:

TYPE:
MODULE | SERVICE | AGENT | ROUTER | TOOL | KERNEL | CONFIG

TIER:
KERNEL | RUNTIME | INFRA | UX

If classification is ambiguous → STOP → ask clarification.

---

PHASE 2 — ORIENT (30-SECOND UNDERSTANDING)

Answer explicitly:
- What does this do?
- Where does it sit in the system?
- Who calls it?
- What does it depend on?

Produce a short orientation summary.

---

PHASE 3 — STRUCTURE & FLOW

STRUCTURE MAP:
- files
- classes
- functions
- exports

FLOW TRACE:
Entry → Handler → Service → Storage / External
          ↓
     Governance / Guards

HOTSPOTS:
| File | Why hot |
|------|---------|

---

PHASE 4 — COMPLIANCE & HEALTH (L9 CANON)

Evaluate against L9 rules:

STRUCTURAL
- correct layer placement
- no bootstrap logic in runtime
- no lifecycle mutation outside GMP

ASYNC
- async I/O correctness
- no sync leakage
- proper timeouts

QUALITY
- logging (no print)
- error handling
- types
- tests exist

ANTI-PATTERNS
| Pattern | Severity | Location |

---

PHASE 5 — IMPACT SCORING

Compute:

Impact Score =
(downstream_blocked × 2)
+ upstream_unlocked
+ cross-layer risk

Classify:
LOW | MEDIUM | HIGH | CRITICAL

---

PHASE 6 — ROUTING DECISION (THE POINT)

Make ONE explicit decision:

| Condition | Route |
|---------|------|
| Code can be reused verbatim | /harvest-analyze |
| Mechanical refactor only | /refactor-sweep |
| Wiring / registration missing | /wire |
| Behavior / lifecycle change | /gmp |
| No action required | STOP |

No mixed outcomes.
No “could also”.

---

PHASE 7 — REPORT (INLINE ONLY)

## 🔍 INSPECT REPORT: {target}

### Classification
Type: {TYPE}
Tier: {TIER}

### Orientation
{what/where/who}

### Structure & Flow
{tree}
{flow}

### Health Summary
| Dimension | Status |
|----------|--------|
| Structure | ✅/❌ |
| Async | ✅/❌ |
| Compliance | ✅/❌ |
| Tests | ✅/❌ |

### Impact
Score: {N}
Level: LOW / MEDIUM / HIGH / CRITICAL

### Decision
➡️ NEXT COMMAND: `/harvest-analyze | /refactor-sweep | /wire | /gmp | STOP`

### Rationale
(1–3 bullet points, factual)

---

STOP CONDITION

After REPORT:
- STOP
- Do NOT chain automatically
- Await user confirmation

---

ANTI-PATTERNS

❌ fixing while inspecting
❌ suggesting code edits
❌ combining multiple routes
❌ skipping classification
❌ soft recommendations

---

CORE PRINCIPLE

Inspect first.
Act second.
Never mix the two.
