<!-- L9_META
l9_schema: 1
parent: l9-code-analysis
origin: migrated-from analyze command v7.0.0
tags: [analysis, structure, hotspots, rapid]
status: active
/L9_META -->

# Analyze Workflow — Rapid Exploration

Fast exploration to understand code before acting (~30 seconds).

## Steps

1. **Orientation** — What is this? What does it do?
2. **Structure map** — Files, classes, functions.
3. **Flow trace** — How data/control flows.
4. **Hotspots** — Critical paths, complexity.
5. **Quick health** — Surface issues.

**Chain:** analyze → understand → evaluate → audit → gmp → fix

## Target types

```text
MODULE | SERVICE | AGENT | ROUTER | TOOL | KERNEL | CONFIG
```

## Output format

```markdown
## ANALYZE: {target}

**Type:** {MODULE/SERVICE/etc.}
**Tier:** {KERNEL/RUNTIME/INFRA/UX}

### Structure
{tree}

### Flows
{diagram}

### Hotspots
| File | Complexity | Why Hot |
|------|------------|---------|

### Quick Health
| Check | Status |
|-------|--------|
| structlog | ✅/❌ |
| async I/O | ✅/❌ |
| type hints | ✅/❌ |
| tests exist | ✅/❌ |

### Recommendation
→ evaluate (if needs deep audit)
→ gmp (if issues found)
→ Continue (if healthy)
```

Auto-chain recommendation: load `l9-ynp` for next action.
