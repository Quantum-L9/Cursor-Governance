---
name: Refined Duplicate Audit
overview: Fix audit script false positive (Pydantic Config classes), create comprehensive documentation with git history context, migration paths, and deterministic future GMP specifications.
todos:
  - id: fix-audit-config
    content: Fix audit script to exclude Pydantic inner Config classes
    status: completed
  - id: create-audit-doc
    content: Create reports/Audit_Duplicate_Classes.md with full analysis
    status: completed
  - id: rerun-audit
    content: Re-run audit to verify false positives eliminated
    status: completed
---

# Refined Duplicate Class Audit

## Executive Summary

The audit script flagged 13 `Config` class occurrences, but these are **Pydantic inner classes** (standard pattern) - NOT problematic duplicates. After deep analysis of the symbolic computation duplicates, the **canonical source is `core/models.py`** (41 callers), not the root `models.py` (3 files, 4 imports).

---

## Phase 0: Fix Audit Script (THIS GMP)

### TODO T1: Fix Pydantic Config False Positive

**File:** [scripts/audit_orphan_classes.py](scripts/audit_orphan_classes.py)  
**Line:** ~87 (in `_extract_class_info` method)  
**Action:** Insert filter for Pydantic inner Config classes

```python
# Skip Pydantic inner Config classes (standard pattern, not duplicates)
if node.name == "Config" and any(
    isinstance(parent, ast.ClassDef) for parent in self._parent_stack
):
    return None
```

### TODO T2: Create Comprehensive Documentation

**File:** `reports/Audit_Duplicate_Classes.md` (new)  
**Action:** Create documentation with all 5 refinements incorporated

---

## Phase 1: Deep Dive Analysis (COMPLETED)

### Git History Context

| File | Commit | Message | Conclusion |
|------|--------|---------|------------|
| `services/symbolic_computation/models.py` | `e9799de` | "refactor(codegen): Reorganize folder structure" | Original location |
| `services/symbolic_computation/models.py` | `ebbad1e` | "feat: L9 Enterprise Upgrade" | Added more backends |
| `core/models.py` | `e9799de` | "refactor(codegen): Reorganize folder structure" | Created during refactor |

**Conclusion:** Root `models.py` is the pre-refactor original. `core/models.py` is the canonical post-refactor version. This is an unfinished migration.

### Import Analysis (Corrected)

| File | Callers | Files | Status |
|------|---------|-------|--------|
| `core/models.py` | 41 | Multiple prod files | CANONICAL |
| `services/symbolic_computation/models.py` | 4 imports | 3 files | Legacy |

**The 3 Legacy Callers:**
1. [services/symbolic_computation/test_symbolic_computation.py](services/symbolic_computation/test_symbolic_computation.py) (line 16)
2. [services/symbolic_computation/README.md](services/symbolic_computation/README.md) (lines 129, 149 - 2 imports)

### Field Compatibility with Migration Path

| Field | Root (Legacy) | Core (Canonical) | Breaking? | Migration Path |
|-------|---------------|------------------|-----------|----------------|
| `variables` | `List[str]` | `Dict[str, float]` | YES | Core version combines variable names + values into single dict |
| `values` | `Dict[str, float]` | (missing) | YES | Merged into `variables` dict - intentional design improvement |
| `result` | `Optional[float]` | `Any` | NO | Widened type, backwards compatible |

### Unused Enum Values (Safe to Delete)

```
BackendType.SYMPY - 0 usages
BackendType.CYTHON - 0 usages  
BackendType.F2PY - 0 usages
BackendType.MPMATH - 0 usages
```

---

## Phase 2: Decision Gate

### Consolidation Risk Assessment

| Risk | Level | Evidence |
|------|-------|----------|
| Production breakage | NONE | 0 prod callers of legacy file |
| Test failures | LOW | Only 1 test file affected |
| Documentation stale | LOW | 1 README needs update |

### Recommendation

**APPROVE consolidation in future GMP** - Risk is minimal, all callers are test/docs.

---

## Phase 3: Current GMP Scope

### IN SCOPE (This GMP)

1. Fix audit script (Pydantic Config filter)
2. Create `reports/Audit_Duplicate_Classes.md`
3. Re-run audit script to verify fix

### OUT OF SCOPE (Future GMP)

1. Delete `services/symbolic_computation/models.py`
2. Update imports in 3 files
3. Run verification tests

---

## Future GMP: Consolidation TODO (Deterministic)

When approved, execute these exact steps:

```
1. DELETE services/symbolic_computation/models.py

2. UPDATE imports in 3 files:
   - test_symbolic_computation.py line 16: 
     from symbolic_computation.models → from symbolic_computation.core.models
   - README.md line 129:
     from symbolic_computation.models → from symbolic_computation.core.models
   - README.md line 149:
     from symbolic_computation.models → from symbolic_computation.core.models

3. VERIFY tests pass:
   pytest services/symbolic_computation/test_*.py -v
   pytest tests/integration/test_symbolic_*.py -v

4. EVIDENCE:
   - All tests green
   - No import errors
   - Coverage maintained
```

---

## L9 Invariants Check

| Protected File | Modified? |
|----------------|-----------|
| docker-compose.yml | NO |
| kernel_loader.py | NO |
| executor.py | NO |
| memory_substrate_service.py | NO |
| websocket_orchestrator.py | NO |