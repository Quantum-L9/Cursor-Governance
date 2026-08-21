---
name: Fix VALID_DERIVE_TYPES Export
overview: Add `VALID_DERIVE_TYPES` to the exports in `core/schemas/__init__.py` - a 2-line surgical fix that restores MCP Memory Service initialization.
todos: []
---

# Fix VALID_DERIVE_TYPES Import Error

## Root Cause

`VALID_DERIVE_TYPES` is defined in `core/schemas/packet_envelope_v2.py` (line 82) but was never exported from `core/schemas/__init__.py`. Two files depend on this import:
- `memory/validators/packet_validator.py`
- `tests/memory/test_packet_validation_v2.py`

## Changes Required

**File:** [core/schemas/__init__.py](core/schemas/__init__.py)

**Edit 1:** Add `VALID_DERIVE_TYPES` to the import from `packet_envelope_v2` (around line 29,