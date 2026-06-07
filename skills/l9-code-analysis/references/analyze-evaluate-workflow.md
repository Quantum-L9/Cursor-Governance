<!-- L9_META
l9_schema: 1
parent: l9-code-analysis
origin: migrated-from analyze_evaluate command v7.0.0
tags: [analysis, evaluation, cross-reference, tech-debt]
status: active
/L9_META -->

# Analyze+Evaluate Workflow — Combined Deep Analysis

Combines analyze + evaluate with cross-referencing.

| Capability | Description |
|------------|-------------|
| Cross-reference | Structure issues → compliance gaps |
| Deduplication | One finding per problem |
| Impact projection | Fix X → unblocks Y |
| Tech debt score | Unified metric |
| Auto-fix candidates | Quick wins flagged |

## Parallel analysis

```text
ANALYZE → Structure, Flows, Hotspots, Dependencies
    ↓ cross-reference
EVALUATE → Patterns, Compliance, Gaps
    ↓ synthesize
COMBINED → Cross-findings, Impact, Tech Debt, Auto-Fix
```

Impact score: `(downstream_blocked × 2) + upstream_unlocked + cross_impact`

## Auto-fix categories

| Category | Time | Examples |
|----------|------|----------|
| AUTO | <1min | imports, formatting, bare except |
| SEMI | 1–5min | docstrings, timeouts, packet logging |
| MANUAL | >5min | refactoring, architecture |

## Output format

```markdown
## ANALYZE+EVALUATE: {target}

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

Auto-chain recommendation: load `l9-ynp` for next action.
