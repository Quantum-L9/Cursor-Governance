---
name: Audit Config Duplicates
overview: Fix false positive in audit script (Pydantic inner Config classes) and document real duplicate classes with consolidation recommendations.
todos:
  - id: fix-audit-script
    content: Fix audit script to exclude Pydantic inner Config classes
    status: pending
  - id: rerun-audit
    content: Re-run audit to verify false positives eliminated
    status: pending
    dependencies:
      - fix-audit-script
  - id: create-audit-doc
    content: Create reports/Audit_Duplicate_Classes.md with consolidation recommendations
    status: pending
    dependencies:
      - rerun-audit
---

# Audit Config Duplicates - Documentation Phase

## Executive Summary

The audit script flagged 13 `Config` class occurrences, but these are **Pydantic inner classes** (standard pattern) - NOT problematic duplicates. This plan fixes the false positive and documents REAL duplicate issues.

## Findings

### False Positive: Pydantic Inner Config Classes (13 occurrences)

These are **NOT duplicates** - they are standard Pydantic model configuration:| Location | Purpose | Verdict |

|----------|---------|---------|

| `api/adapters/calendar_adapter/schemas.py:49,71` | Pydantic model config | IGNORE |

| `api/adapters/email_adapter/schemas.py:49,71` | Pydantic model config | IGNORE |

| `api/adapters/twilio_adapter/schemas.py:49,71` | Pydantic model config | IGNORE |

| `core/tools/base_registry.py:49,79` | Pydantic model config | IGNORE |

| `memory/substrate_models.py:398` | Pydantic model config | IGNORE |

| `services/research/research_api.py:37,63` | Pydantic model config | IGNORE |

| `services/symbolic_computation/*.py` | Pydantic model config | IGNORE |

### Real Duplicate: Symbolic Computation Models

**Problem:** Two files define identical classes:

```javascript
services/symbolic_computation/
├── models.py              <- OLD (168 lines)
├── core/
│   └── models.py          <- NEW (135 lines)
└── core.py                <- ALSO has overlapping classes
```

| Class | models.py | core/models.py | Difference |

|-------|-----------|----------------|------------|

| `BackendType` | 6 values | 3 values | Root has more backends |

| `CodeLanguage` | 4 values | 4 values | Same |

| `ComputationRequest` | Full | Simplified | Root has more fields |

| `ComputationResult` | Full | Simplified | Root has more fields |

| `CodeGenRequest` | Full | Minimal | Root has more fields |

| `CodeGenResult` | Full | Minimal | Root has more fields |**Recommendation:** Keep `services/symbolic_computation/models.py` (more complete), delete `core/models.py`, update imports.

## Implementation Tasks

### Task 1: Fix Audit Script False Positive

Update [scripts/audit_orphan_classes.py](scripts/audit_orphan_classes.py) to exclude Pydantic inner `Config` classes from duplicate detection.**Change:** Add filter to `find_duplicate_classes()` function:

```python
# Exclude Pydantic inner Config classes (standard pattern)
if name == "Config":
    continue
```



### Task 2: Document Symbolic Computation Consolidation (Audit Only)

Create documentation file `reports/Audit_Duplicate_Classes.md` with:

1. List of duplicates detected
2. Which file is canonical
3. Which files to delete
4. Import paths that need updating
5. Risk assessment

**No code changes in this phase** - documentation only as requested.

## Risk Assessment

| Risk | Level | Mitigation |

|------|-------|------------|

| Script fix breaks detection | Low | Only filters `Config` by name |

| Missing real duplicates | Low | Re-run after fix verifies |

| Symbolic consolidation breaks imports | Medium | Future GMP with full test coverage |

## L9 Invariants Check

| File | Touched? |

|------|----------|

| docker-compose.yml | NO |

| kernel_loader.py | NO |

| executor.py | NO |

| memory_substrate_service.py | NO |
