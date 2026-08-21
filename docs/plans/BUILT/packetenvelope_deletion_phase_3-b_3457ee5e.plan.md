---
name: PacketEnvelope Deletion Phase 3-B
overview: Delete 4 superseded PacketEnvelope files, verify SDK installation, and run full test suite to confirm no regressions.
todos:
  - id: verify-sdk
    content: Verify constellation-node-sdk is installed and importable
    status: completed
  - id: delete-test-file
    content: Delete tests/unit/test_packet_envelope.py
    status: completed
  - id: delete-bridge
    content: Delete engine/packet/bridge.py
    status: completed
  - id: delete-l9core
    content: Delete l9_core/ directory (models.py + empty __init__.py)
    status: completed
  - id: delete-envelope
    content: Delete engine/packet/packet_envelope.py
    status: completed
  - id: update-prohibition
    content: "Drop enhanced scanner from archive: AST-hardened, ALLOWED_DEFINITION_FILES=set()"
    status: completed
  - id: add-scanner-tests
    content: Add tests/unit/test_check_packet_envelope_prohibited.py (8 tests for the scanner)
    status: completed
  - id: verify-scanner
    content: "Run scanner: python tools/check_packet_envelope_prohibited.py must print OK"
    status: completed
  - id: run-tests
    content: Run full test suite to verify no regressions (expect 88 passed minus deleted tests)
    status: completed
isProject: false
---

# PacketEnvelope Deletion and Phase 3-B Verification

## Pre-Deletion: Verify SDK Installation

The `constellation-node-sdk` is already declared in [pyproject.toml](pyproject.toml) line 23:
```toml
constellation-node-sdk = {git = "https://github.com/cryptoxdog/Gate_SDK.git"}
```

Verify the SDK is installed and importable before proceeding:
```bash
python -c "from constellation_node_sdk import TransportPacket, create_transport_packet; print('SDK OK')"
```

## Files to DELETE (4 files + 1 directory)

| File | Reason | Impact |
|------|--------|--------|
| `engine/packet/packet_envelope.py` | Canonical definition superseded by `TransportPacket` from SDK | Tests and chassis_contract.py need migration |
| `l9_core/models.py` | Legacy duplicate `PacketEnvelope` definition | Only used by `engine/packet/bridge.py` (also being deleted) |
| `l9_core/` (entire directory) | Empty `__init__.py` + deleted `models.py` | No other contents |
| `engine/packet/bridge.py` | Old thin wrapper using `l9_core.models.PacketEnvelope` | Replaced by `engine/packet_bridge.py` using SDK |
| `tests/unit/test_packet_envelope.py` | 527-line test file for deleted `PacketEnvelope` class | Tests no longer applicable |

## Dependency Analysis

Files that import from deleted modules:
- `engine/packet/bridge.py` imports from `l9_core.models` (being deleted, so no issue)
- `tests/unit/test_packet_envelope.py` imports from `engine/packet/packet_envelope` (being deleted)
- `engine/packet/chassis_contract.py` imports from `engine/packet/packet_envelope` (needs UPDATE in separate phase)

## Phase 3-B Execution Steps

### Step 1: SDK Verification
Run import test to confirm SDK is installed and functional.

### Step 2: Delete Files (Exact Commands)

Remove the superseded files in this order:

```bash
# 1. Tests first
git rm tests/unit/test_packet_envelope.py

# 2. Wrapper that uses l9_core
git rm engine/packet/bridge.py

# 3. Legacy l9_core directory
git rm l9_core/models.py
git rm l9_core/__init__.py
rmdir l9_core

# 4. Canonical definition last
git rm engine/packet/packet_envelope.py
```

### Step 3: Drop Enhanced Scanner from Archive

Replace [tools/check_packet_envelope_prohibited.py](tools/check_packet_envelope_prohibited.py) with the AST-hardened version from the archive.

**Enhancements over original scanner:**
- `ALLOWED_DEFINITION_FILES = set()` (empty - no definitions allowed post-Phase-3-B)
- AST-based bare name detection: catches `PacketEnvelope(...)` without an import
- Attribute usage detection: catches `m.PacketEnvelope` for aliased references
- Hardened against migration files that copy-paste the class name

### Step 4: Add Scanner Test Suite

Add [tests/unit/test_check_packet_envelope_prohibited.py](tests/unit/test_check_packet_envelope_prohibited.py) from the archive.

**8 tests verifying:**
- Import pattern detection (PE-001 through PE-007)
- Class definition detection (PE-DEF)
- AST-based bare name detection
- Attribute usage detection
- Invariant: `ALLOWED_DEFINITION_FILES` is empty

### Step 5: Verify Scanner
```bash
python tools/check_packet_envelope_prohibited.py
```
Must print `OK` (no violations in remaining codebase).

### Step 6: Run Full Test Suite
```bash
PYTHONPATH=. pytest tests/ -x --tb=short -q
```

Expected: 88 passed (minus `test_packet_envelope.py` tests which are deleted)

The pre-existing failure in `test_compliance_checker.py` is unrelated to this change.

## Files NOT Deleted (Require Separate Migration Phase)

These files use `PacketEnvelope` but need migration to `TransportPacket`, not deletion:
- `engine/packet/chassis_contract.py` - Chassis bridge (active)
- `chassis/actions.py` - Chassis integration (active)
- `engine/contract_enforcement.py` - Contract checks (active)
- `engine/convergence_controller_patch.py` - Patch file (needs verification)
- `engine/compliance/audit.py`, `engine/compliance/pii.py` - Compliance (active)

## Rollback

If tests fail unexpectedly:
```bash
git checkout HEAD -- engine/packet/packet_envelope.py engine/packet/bridge.py l9_core/ tests/unit/test_packet_envelope.py
```
