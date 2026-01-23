---
name: pr
version: "1.0.0"
description: "PR merge orchestrator — analyze, resolve, merge via GMP"
auto_chain: gmp
---

# /pr — PR Merge Orchestrator

## USAGE

```
/pr                  # Analyze all open PRs
/pr #45              # Merge specific PR
/pr #45,#46          # Batch merge
```

## CHAIN

```
/pr → DISCOVERY → DAG → /analyze_evaluate → /gmp → /wire → CLOSE → /ynp
```

## PHASES

| # | Phase | Action |
|---|-------|--------|
| 1 | DISCOVERY | `gh pr list --state open` → inventory |
| 2 | DAG | Detect dependencies → topological sort → merge order |
| 3 | ANALYZE | `/analyze_evaluate` per PR → identify gaps/conflicts |
| 4 | RESOLVE | Generate TODO plan per PR |
| 5 | EXECUTE | `/gmp` per PR in order |
| 6 | WIRE | `/wire` new components |
| 7 | CLOSE | `gh pr close` with comment |

## CONFLICT TYPES

| Type | Detection | Resolution |
|------|-----------|------------|
| NONE | Clean merge-tree | Direct merge |
| CONTENT | Conflict markers | Manual resolve |
| DEPENDENCY | File A needs file B | Order matters |
| DUPLICATE | Same file in multiple PRs | Pick latest |

## DAG RULES

PR A depends on PR B if:
- A modifies file B creates
- A imports from module B adds
- A expands content B introduces

## OUTPUT

```markdown
## PR #{number}: {title}

**Conflict:** NONE | CONTENT | DEPENDENCY
**Depends On:** #{x}, #{y} | None

### TODO (for /gmp)
| T# | File | Action | Description |
|----|------|--------|-------------|

### After /gmp
- /wire {new_components}
- gh pr close {number}
```

## STOP CONDITIONS

- Circular dependency → STOP, report cycle
- Protected file → Route to KERNEL GMP
- > 100 files → Suggest breaking PR

--- End Command ---
