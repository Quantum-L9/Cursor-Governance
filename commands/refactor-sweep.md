name: refactor-sweep
version: "2.0.0"
description: "Deterministic refactor impact analysis and execution gating (NO code changes)"
auto_chain: gmp

# /refactor-sweep — Deterministic Refactor Impact Sweep

NON-NEGOTIABLE
- READ-ONLY
- NO code modification
- NO rewriting
- NO automatic fixes
- This command ANALYZES, it does NOT act

---

PURPOSE

Determine whether a proposed refactor is:
1. Safe mechanical change
2. Harvest/use eligible
3. GMP-required (high risk)
4. Architecturally forbidden

This command exists to PREVENT sloppy refactors.

---

USAGE

/refactor-sweep "rename foo to bar"
/refactor-sweep "replace print with logger"
/refactor-sweep "add timeout to httpx calls"

Input MUST describe:
- intent
- scope
- transformation rule

If intent is vague → STOP → ask clarification.

---

CHAIN

/refactor-sweep
→ DISCOVERY
→ CLASSIFICATION
→ IMPACT ANALYSIS
→ GOVERNANCE DECISION
→ REPORT
→ STOP

---

PHASE 1 — DISCOVERY (EXHAUSTIVE)

Locate ALL instances related to the refactor intent.

Commands:
rg "{primary_pattern}" --type py -n

Output table:
| File | Line | Match | Context |
|------|------|-------|---------|
| a.py | 20 | foo() | function call |
| b.py | 35 | foo | attribute |

If zero matches → STOP → report “no-op”.

---

PHASE 2 — CLASSIFICATION (L9 LAYERING)

For EACH file, classify:

| File | Layer | Domain |
|------|------|--------|
| api/x.py | runtime | API |
| bootstrap/y.py | bootstrap | init |
| memory/z.py | substrate | memory |

Flags:
- bootstrap code
- lifecycle code
- async boundary code
- protected files

---

PHASE 3 — IMPACT ANALYSIS (DETERMINISTIC)

For EACH instance, assess:

| Dimension | Result |
|---------|--------|
| Mechanical (sed-safe) | YES / NO |
| Requires logic change | YES / NO |
| Async boundary affected | YES / NO |
| Import graph affected | YES / NO |
| Public contract change | YES / NO |

Rules:
- If ANY instance is NOT mechanical → mark ENTIRE sweep as NON-MECHANICAL
- If ANY protected file involved → GMP REQUIRED

---

PHASE 4 — GOVERNANCE DECISION

Determine execution path:

| Outcome | Action |
|------|--------|
| All mechanical, no protected files | Eligible for /harvest-use |
| Mixed mechanical + semantic | GMP REQUIRED |
| Lifecycle / bootstrap impact | GMP REQUIRED |
| Cross-layer violation | FORBIDDEN |

No gray areas.
No partial approvals.

---

PHASE 5 — REPORT (INLINE ONLY)

Report in workspace chat:

## 🔍 REFACTOR SWEEP REPORT

**Intent:** rename foo → bar

### Summary
| Metric | Value |
|------|------|
| Files affected | N |
| Instances found | N |
| Layers touched | api, runtime |
| Protected files | none |

### Impact Classification
- Mechanical only: ✅
- Async boundary affected: ❌
- Import graph change: ❌

### Governance Decision
✅ Eligible for /harvest-use  
❌ Direct refactor NOT permitted  
❌ Manual edits NOT permitted

### Next Step
Run:
`/harvest-plan` → `/harvest-use`
or
`/gmp` (if required)

---

STOP CONDITION

After REPORT:
- STOP
- Do NOT refactor
- Do NOT write code
- Do NOT auto-chain

---

ANTI-PATTERNS

❌ rewriting code
❌ “small fixes while here”
❌ skipping classification
❌ partial execution
❌ mixing with /wire directly

---

CORE PRINCIPLE

Refactors are not edits.
They are SYSTEM EVENTS.
Treat them accordingly.
