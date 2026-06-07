<!-- L9_META
l9_schema: 1
parent: l9-code-analysis
origin: migrated-from evaluate command v7.0.0
tags: [evaluation, compliance, gaps, audit]
status: active
/L9_META -->

# Evaluate Workflow — Deep Evaluation

Comprehensive audit across six dimensions → actionable GMP TODOs.

## Dimensions

1. **Workflow state** — Phase, TODOs, blockers (`workflow_state.md` when present).
2. **Tier health** — KERNEL/RUNTIME/INFRA/UX compliance.
3. **GMP compliance** — Phase gates, missing steps.
4. **Code quality** — L9 patterns, anti-patterns.
5. **Dependencies** — Imports, circular refs, orphans.
6. **Gaps** — Missing vs production-ready.

## L9 health checks

| Check | Required |
|-------|----------|
| structlog | Not logging/print |
| httpx | Not requests/aiohttp |
| async I/O | Async def for I/O |
| pydantic v2 | model_config, not Config |
| packet logging | Critical ops → PacketEnvelope |
| error handling | try/except + recovery |
| timeouts | External calls have timeout |

## Anti-patterns

| Pattern | Severity |
|---------|----------|
| Bare except | CRITICAL |
| sync in async | CRITICAL |
| global state | HIGH |
| missing types | MEDIUM |
| no docstring | MEDIUM |

## Output format

```markdown
## EVALUATE: {target}

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

Auto-chain recommendation: load `l9-ynp` for next action.
