---
name: l9-gap-analysis
description: Perform read-only delta gap analysis against a target state with scoring and optional actionable recommendations. Use when assessing readiness, missing pieces, compliance drift, or percent-complete status.
---

name: gap-analysis
version: "3.1.0"
description: "Standalone gap analysis vs target state — extract, compare, score %, report, stop"
auto_chain: n

# /gap-analysis — Standalone Delta Analysis (%-based)

RULES (ABSOLUTE)

- READ-ONLY
- NO fixes
- NO wiring
- NO harvesting
- NO refactors
- NO execution
- NO auto follow-ups

This command ANALYZES ONLY.

---

USAGE

/gap-analysis path/to/file.py
/gap-analysis path/to/dir/
/gap-analysis file1.py file2.py
/gap-analysis --target L9
/gap-analysis --target prod-ready

Target defaults to: L9_CANON

---

PURPOSE

Given explicit files:
1. Extract current state
2. Compare against a target state
3. Identify gaps
4. Score gaps as %
5. Report
6. STOP

---

CHAIN

/gap-analysis
→ EXTRACT
→ NORMALIZE
→ COMPARE
→ SCORE
→ REPORT
→ STOP

---

PHASE 1 — EXTRACT

For each provided file:
- identify role (module / service / agent / config)
- identify layer (kernel / runtime / infra / ux)
- identify responsibilities
- identify dependencies
- identify lifecycle involvement

Static analysis only.

---

PHASE 2 — NORMALIZE

Reduce extracted info into dimensions:

- Structure
- Lifecycle
- Async / Concurrency
- Error handling
- Observability
- Configuration
- Tests / verification

Each dimension scored:
- 0%   = absent
- 50%  = partial / inconsistent
- 100% = present / compliant

---

PHASE 3 — COMPARE (TARGET-BASED)

Compare normalized state against target expectations.

Targets may include:
- L9_CANON
- prod-ready
- scale-ready
- k8s-ready
- custom (string)

For each dimension:
Gap % = Target % − Current %

Only report gaps where Gap % > 0.

---

PHASE 4 — SCORE

For each gap compute:

| Gap | Dimension | Gap % | Scope % |
|-----|-----------|-------|---------|

Guidelines:
- Scope % reflects blast radius (local → cross-layer)
- No subjective labels
- No prioritization logic beyond raw %s

---

PHASE 5 — REPORT (INLINE ONLY)

## GAP ANALYSIS

Target: {target}

### Files Analyzed
- path/file.py
- path/file2.py

### Coverage Summary
| Dimension | Coverage % |
|----------|------------|
| Structure | 85% |
| Lifecycle | 40% |
| Async | 70% |
| Observability | 20% |

### Gaps
| Gap | Dimension | Gap % | Scope % |
|-----|----------|-------|---------|
| Lifecycle isolation missing | Lifecycle | 60% | 80% |
| No I/O timeouts | Async | 30% | 40% |

### Notes
- % = distance from target
- No fixes proposed
- No execution implied

---

STOP CONDITION

After report:
- STOP
- Await user input

---

<!-- migrated-from: gap-analysis.md -->

---
name: gap-analysis
version: "1.1.0"
description: "Identify gaps vs target state"
before_chain: rules
auto_chain: ynp
---

# /gap-analysis — Gap Identification

## WHAT IT DOES

Compare current state vs target → identify gaps.

---

## EXECUTION

### 1. DEFINE TARGET

```
TARGET STATE:
├── All L9 patterns
├── No anti-patterns
├── Tests exist
├── Docs complete
├── GMP phases done
```

### 2. ASSESS CURRENT

| Dimension | Current | Target | Gap |
|-----------|---------|--------|-----|
| Patterns | 80% | 100% | 20% |
| Tests | 60% | 100% | 40% |
| Docs | 50% | 100% | 50% |

### 3. PRIORITIZE GAPS

| Priority | Gap | Impact | Effort |
|----------|-----|--------|--------|
| 🔴 | Missing tests | High | Medium |
| 🟠 | Anti-patterns | Medium | Low |

---

## OUTPUT

```markdown
## 📊 GAP ANALYSIS: {scope}

### Current vs Target
| Dimension | Current | Target | Gap |
|-----------|---------|--------|-----|

### Gaps (Prioritized)
| # | Gap | Priority | Fix |
|---|-----|----------|-----|

### Effort Estimate
**Total gaps:** N
**Effort:** {estimate}

### Recommended GMPs
| GMP | Scope | Gaps Addressed |
|-----|-------|----------------|
```

→ **Auto-chains to /ynp**

--- End Command ---
