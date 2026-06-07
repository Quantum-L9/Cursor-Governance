<!-- L9_META
l9_schema: 1
parent: l9-gap-analysis
origin: migrated-from gap-analysis command v1.1.0
tags: [gap-analysis, prioritized, gmp, recommendations]
status: active
/L9_META -->

# Gap Analysis — Prioritized (with GMP routing)

Compare current state vs target → identify gaps with priority and effort.

## Define target

```text
TARGET STATE:
├── All L9 patterns
├── No anti-patterns
├── Tests exist
├── Docs complete
└── GMP phases done
```

## Assess current

| Dimension | Current | Target | Gap |
|-----------|---------|--------|-----|
| Patterns | 80% | 100% | 20% |
| Tests | 60% | 100% | 40% |
| Docs | 50% | 100% | 50% |

## Prioritize gaps

| Priority | Gap | Impact | Effort |
|----------|-----|--------|--------|
| CRITICAL | Missing tests | High | Medium |
| HIGH | Anti-patterns | Medium | Low |

## Output format

```markdown
## GAP ANALYSIS: {scope}

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

Auto-chain recommendation: load `l9-ynp` for next action. Still read-only — recommendations only, no execution.
