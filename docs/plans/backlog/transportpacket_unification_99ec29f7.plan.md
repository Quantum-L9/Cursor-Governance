---
name: TransportPacket Unification
overview: Unify on TransportPacket as the canonical packet type, deprecating PacketEnvelope. Continue on feat/transport-packet-migration-clean branch with proper CI/review flow.
todos:
  - id: sync-gate-transport
    content: Add timeout_ms to gate/engine/boundary/transport_codec.py PacketHeader
    status: pending
  - id: run-tests
    content: Run full test suite including test_transport_codec.py, test_boundary.py, test_ingress_validator.py
    status: pending
  - id: commit-changes
    content: Commit all modified files with message describing timeout_ms addition and handler fixes
    status: pending
  - id: push-branch
    content: Push to origin/feat/transport-packet-migration-clean
    status: pending
  - id: open-pr
    content: Open PR targeting main with migration context
    status: pending
isProject: false
---

# TransportPacket Unification Plan

## Current State

- **Branch**: `feat/transport-packet-migration-clean` (already tracking remote)
- **Modified files** (uncommitted):
  - `engine/boundary/transport_codec.py` — `timeout_ms` added
  - `gate/engine/handlers.py` — dict→PacketEnvelope conversion added
  - `tests/test_dispatch.py` — updated to use PacketEnvelope
  - `tests/integration/test_end_to_end.py` — updated to use PacketEnvelope

## Problem: Duplicate Codebases

There are **two copies** of the boundary layer:

- `engine/boundary/` — canonical location
- `gate/engine/boundary/` — duplicate (missing `timeout_ms`)

Both need to stay in sync until one is removed.

## Migration Phases

### Phase 1: Schema Alignment (This PR)

**Goal**: Add `timeout_ms` to both TransportPacket locations, commit, push, open PR.

Files to update:

- `engine/boundary/transport_codec.py` — already done
- `gate/engine/boundary/transport_codec.py` — needs `timeout_ms` added

Tests to verify:

- `tests/test_transport_codec.py`
- `tests/test_boundary.py`
- `tests/test_ingress_validator.py`
- All 17 pack tests (already passing)

### Phase 2: Consolidate Boundary Layer (Future PR)

Remove duplicate `gate/engine/boundary/` and have `gate/engine/handlers.py` import from `engine/boundary/` instead.

Affected files:

- `gate/engine/handlers.py` — change imports
- `gate/engine/boundary/`* — delete entire directory

### Phase 3: Deprecate PacketEnvelope (Future PR)

Replace all `chassis.packet_envelope.PacketEnvelope` usage with `engine.boundary.transport_codec.TransportPacket`.

Affected files (13 total):

- `app/engines/chassis_contract.py`
- `client/auth.py`
- `client/execute_client.py`
- `gate/engine/dispatch.py`
- `gate/engine/handlers.py`
- `l9/chassis/node_client.py`
- `chassis/__init__.py`
- `chassis/router.py`
- `chassis/security.py`
- Tests: `test_dispatch.py`, `test_end_to_end.py`, `test_ingress_hardening.py`, `test_signature_modes.py`

### Phase 4: Remove PacketEnvelope (Future PR)

Delete `chassis/packet_envelope.py` and `chassis/tenant_context.py` after all consumers migrated.

## Immediate Actions (Phase 1)

1. Add `timeout_ms` to `gate/engine/boundary/transport_codec.py`
2. Run full test suite
3. Commit all changes with descriptive message
4. Push to `feat/transport-packet-migration-clean`
5. Open PR targeting `main`

## CI/Review Requirements

- All tests must pass
- PR requires code review before merge
- GitHub Actions CI must be green
