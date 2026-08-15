# Program Execution compiler module

Logical name: `l9-devpack-compiler`.

This directory is the in-tree compiler boundary for Program Execution. It is a
**module of this repository**, not a separate git repository.

Authority: `environment/program-execution/campaigns/PE_COMPILER_MODULE_ALIGNMENT.yaml`
(AUTH-001, 2026-08-14).

## Owns

- `program-execution.intent.v1` and intent-resolution IR
- Intent Resolver and Program Synthesizer
- DPK / repository-truth consumption used to compile Blueprint v2
- Official Blueprint validator adapter (calls the existing validator; does not
  fork it)
- Minimal `program-execution intent` front door

## Must not own

- Mutable Program runtime, leases, attempts, gate results, or handoff receipts
- A second Controller or scheduler
- Peer-local policy or adapter-owned semantics

The existing Program Execution Controller remains the only runtime authority.

## Campaigns

| Campaign | Role |
|---|---|
| `cc-pe-intent-compiler-v1` | Build this module from `CONTRACT_SOURCE.md` |
| `l9-devpack-program-execution-hardening` | Harden this same module (provenance, proof semantics, PE v2 projection) |

Implementation files land here when those campaigns execute. This README is the
module home and wiring declaration only.
