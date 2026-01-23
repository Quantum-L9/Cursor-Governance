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
