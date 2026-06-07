<!-- L9_META
l9_schema: 1
parent: l9-gap-analysis
origin: migrated-from gap-analysis command v3.1.0
tags: [gap-analysis, read-only, scoring, delta]
status: active
/L9_META -->

# Gap Analysis — Standalone Delta (%-based)

## Absolute rules

- READ-ONLY
- NO fixes, wiring, harvesting, refactors, execution, or auto follow-ups
- ANALYZES ONLY → STOP after report

## Usage

```text
/gap-analysis path/to/file.py
/gap-analysis path/to/dir/
/gap-analysis --target L9
/gap-analysis --target prod-ready
```

Target defaults to: `L9_CANON`

## Phases

### 1 — Extract

Per file: role, layer, responsibilities, dependencies, lifecycle involvement. Static analysis only.

### 2 — Normalize

Dimensions: Structure, Lifecycle, Async/Concurrency, Error handling, Observability, Configuration, Tests/verification.

Score each: 0% absent | 50% partial | 100% present/compliant.

### 3 — Compare

Gap % = Target % − Current %. Report only Gap % > 0.

### 4 — Score

| Gap | Dimension | Gap % | Scope % |

Scope % reflects blast radius (local → cross-layer). No subjective prioritization beyond raw %s.

## Report template

```markdown
## GAP ANALYSIS

Target: {target}

### Files Analyzed
- path/file.py

### Coverage Summary
| Dimension | Coverage % |
|-----------|------------|

### Gaps
| Gap | Dimension | Gap % | Scope % |
|-----|-----------|-------|---------|

### Notes
- % = distance from target
- No fixes proposed
- No execution implied
```

**STOP** after report. Await user input.
