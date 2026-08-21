---
name: Enhanced Duplicate Audit
overview: Fix audit script false positive (Pydantic Config), document symbolic computation duplicates with full import analysis and field compatibility matrix, provide consolidation recommendations.
todos:
  - id: fix-audit-config
    content: Fix audit script to exclude Pydantic inner Config classes
    status: pending
  - id: rerun-audit
    content: Re-run audit to verify false positives eliminated
    status: pending
    dependencies:
      - fix-audit-config
  - id: create-audit-doc
    content: Create reports/Audit_Duplicate_Classes.md with full analysis
    status: pending
    dependencies:
      - rerun-audit
---

# Enhanced Duplicate Class Audit - With Deep Analysis

## Executive Summary

The audit script flagged 13 `Config` class occurrences, but these are **Pydantic inner classes** (standard pattern) - NOT problematic duplicates. After deep analysis of the symbolic computation duplicates, the **canonical source is `core/models.py`** (41 callers), not the root `models.py` (4 callers).---

## Phase 0: False Positive Identification

### Pydantic Inner Config Classes (13 occurrences) - IGNORE

These are standard Pydantic model configuration, NOT duplicates:| Location | Verdict |

|----------|---------|

| `api/adapters/*/schemas.py` | IGNORE (Pydantic pattern) |

| `core/tools/base_registry.py` | IGNORE (Pydantic pattern) |

| `memory/substrate_models.py` | IGNORE (Pydantic pattern) |

| `services/*/config.py` | IGNORE (Pydantic pattern) |**Fix:** Update [scripts/audit_orphan_classes.py](scripts/audit_orphan_classes.py) to exclude classes named `Config`.---

## Phase 1: Symbolic Computation Deep Dive (COMPLETED)

### Import Analysis Results

| File | Import Count | Callers |

|------|--------------|---------|

| `core/models.py` | **41** | All production code, API routes, tests |

| `models.py` (root) | **4** | Only docs, examples, one test file |**Verdict:** `core/models.py` is the CANONICAL source.

### Enum Difference Analysis

| Enum Value | models.py (root) | core/models.py | Used in Codebase? |

|------------|-----------------|----------------|-------------------|

| NUMPY | Yes | Yes | Yes |

| MATH | Yes | Yes | Untested |

| MPMATH | Yes | Yes | Untested |

| SYMPY | Yes | No | **NO** |

| CYTHON | Yes | No | **NO** |

| F2PY | Yes | No | **NO** |**Verdict:** Extra enum values in root `models.py` are UNUSED. Safe to delete.

### Field Compatibility Matrix

#### ComputationRequest

| Field | models.py (root) | core/models.py | Breaking? |

|-------|-----------------|----------------|-----------|

| expression | str (required) | str (required) | No |

| variables | `List[str]` | `Dict[str, float]` | **YES - TYPE DIFFERS** |

| backend | BackendType | BackendType | No |

| values | `Dict[str, float]` | (missing) | **YES** |

| use_cache | bool | (missing) | **YES** |

| options | (missing) | `Dict[str, Any]` | **YES** |

#### ComputationResult

| Field | models.py (root) | core/models.py | Breaking? |

|-------|-----------------|----------------|-----------|

| success | bool | (missing) | **YES** |

| result | `Optional[float] `| `Any` | Type differs |

| backend_used | BackendType | str | Type differs |

| execution_time_ms | float | float | No |

| cache_hit | (missing) | bool | **YES** |

| expression_hash | (missing) | str | **YES** |**Verdict:** Models are NOT drop-in compatible. However, since `core/models.py` has 41 production callers, it defines the actual contract. Root `models.py` is legacy.

### Callers of Root models.py (4 files to update)

| File | Type | Action |

|------|------|--------|

| `test_symbolic_computation.py` | Test | Update imports |

| `README.md` | Docs | Update examples |

| `codegen/.../examples_symbolic_computation.py` | Example | Update imports |---

## Phase 2: Decision Gate

| Criterion | Status |

|-----------|--------|

| Canonical source identified | `core/models.py` (41 callers) |

| All callers traced | Yes (4 legacy, 41 production) |

| Breaking changes identified | Yes (incompatible field types) |

| Unused enum values confirmed | Yes (SYMPY, CYTHON, F2PY unused) |**Consolidation Risk: LOW** - Only 4 files use legacy models, all are tests/docs/examples.---

## Phase 3: Recommendations

### Immediate Actions (This GMP)

1. **Fix audit script** - Exclude Pydantic inner `Config` classes
2. **Create audit document** - `reports/Audit_Duplicate_Classes.md`

### Future GMP: Symbolic Computation Consolidation

1. **DELETE** `services/symbolic_computation/models.py` (legacy, 168 lines)
2. **UPDATE** 4 files to import from `core.models` instead
3. **VERIFY** no runtime breaks in tests

### Files to Modify in Future GMP

| File | Action |

|------|--------|

| `services/symbolic_computation/models.py` | DELETE |

| `services/symbolic_computation/test_symbolic_computation.py` | Update imports |

| `services/symbolic_computation/README.md` | Update examples |

| `codegen/code-gen-files/examples_symbolic_computation.py` | Update imports |---

## Risk Assessment

| Risk | Level | Mitigation |

|------|-------|------------|

| Script fix breaks detection | Low | Only filters `Config` by name |

| Consolidation breaks imports | Low | Only 4 files use legacy |

| Field incompatibility | None | Legacy callers don't run in prod |

## L9 Invariants Check

| File | Touched? |

|------|----------|

| docker-compose.yml | NO |

| kernel_loader.py | NO |

| executor.py | NO |

| memory_substrate_service.py | NO |