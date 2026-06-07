<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [forge, autonomous, gmp]
status: active
/L9_META -->

# Forge Workflow

## 1. Scope lock

```markdown
## FORGE SCOPE
**Task:** {description}
**GMPs:** {count}
**Files:** {list}
**Tier:** KERNEL | RUNTIME | INFRA | UX
```

## 2. Execute GMPs

For each GMP: phases 0–6, auto-fix validation failures, generate report.

## 3. Deliver

| Artifact | Required |
|----------|----------|
| Code | yes |
| Tests | yes |
| Docs | if new API |
| Report | yes |

## Output

```markdown
## FORGE COMPLETE

**GMPs:** N executed
**Files:** N modified
**Tests:** passing

### Deliverables
- [x] Code implemented
- [x] Tests added
- [x] Reports generated
```

Auto-chain to l9-ynp when appropriate.
