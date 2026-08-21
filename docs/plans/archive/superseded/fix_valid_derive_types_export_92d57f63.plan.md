---
name: Fix VALID_DERIVE_TYPES Export
overview: Add `VALID_DERIVE_TYPES` to exports in `core/schemas/__init__.py` and `universal_schema.py` for consistency - restores MCP Memory Service initialization.
todos:
  - id: add-import-init
    content: Add VALID_DERIVE_TYPES to import statement in core/schemas/__init__.py (line ~29)
    status: pending
  - id: add-export-init
    content: Add VALID_DERIVE_TYPES to __all__ list in core/schemas/__init__.py (line ~113)
    status: pending
  - id: add-import-universal
    content: Add VALID_DERIVE_TYPES to import in core/schemas/universal_schema.py (line ~22)
    status: pending
  - id: add-export-universal
    content: Add VALID_DERIVE_TYPES to __all__ list in core/schemas/universal_schema.py (line ~77)
    status: pending
  - id: verify
    content: Run verification command to confirm fix
    status: pending
---

# Fix VALID_DERIVE_TYPES Import Error

## Root Cause

`VALID_DERIVE_TYPES` is defined in `core/schemas/packet_envelope_v2.py` (line 82) but was never exported from `core/schemas/__init__.py`. Two files depend on this import:

- `memory/validators/packet_validator.py`
- `tests/memory/test_packet_validation_v2.py`

## Changes Required

### File 1: [core/schemas/__init__.py](core/schemas/__init__.py) (Required)

**Edit 1:** Add `VALID_DERIVE_TYPES` to the import from `packet_envelope_v2` (line 29, after `DeriveType`):

```python
    DeriveType,
    VALID_DERIVE_TYPES,  # ADD THIS LINE
    # Search Models
```

**Edit 2:** Add `VALID_DERIVE_TYPES` to `__all__` list (line 113, after `"DeriveType"`):

```python
    "DeriveType",
    "VALID_DERIVE_TYPES",  # ADD THIS LINE
    # Search Models
```

### File 2: [core/schemas/universal_schema.py](core/schemas/universal_schema.py) (Consistency)

**Edit 3:** Add `VALID_DERIVE_TYPES` to the import from `core.schemas` (line 31, after `SemanticSearchResult`):

```python
    SemanticSearchResult,
    VALID_DERIVE_TYPES,  # ADD THIS LINE
)
```

**Edit 4:** Add `VALID_DERIVE_TYPES` to `__all__` list (line 87, after `"SemanticSearchResult"`):

```python
    "SemanticSearchResult",
    "VALID_DERIVE_TYPES",  # ADD THIS LINE
    # === Research Factory Models ===
```

## Verification

After fix, run:

```bash
python -c "from core.schemas import VALID_DERIVE_TYPES; print(VALID_DERIVE_TYPES)"
python -c "from core.schemas.universal_schema import VALID_DERIVE_TYPES; print(VALID_DERIVE_TYPES)"
```

Expected output for both: `{'direct', 'inferred', 'synthesized'}`