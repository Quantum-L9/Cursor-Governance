# Program Execution System Templates

This distribution contains two aligned, reusable siblings:

1. **Program Execution Blueprint**: the design-time authority pack for an Execution Program.
2. **Program Execution Controller**: the runtime authority that admits, schedules, constrains, verifies, recovers, and records execution.

The Blueprint defines **what must happen, why, in what order, under whose authority, and what evidence proves completion**. The Controller defines **what may run now, against which exact state, under which authorization, and what durable receipt advances runtime state**.

## Canonical boundary

```text
Verified sources and decisions
          |
          v
Program Execution Blueprint
(intent, authority, dependencies, ceilings, gates)
          |
          | immutable import + source digests
          v
Program Execution Controller
(runtime state, leases, attempts, verification, recovery)
          |
          | handoff receipt + evidence references
          v
Program owner accepts program verdict or issues a superseding Blueprint
```

The Controller never edits Blueprint authority in place. It may narrow a task contract, but it may not widen scope, action permissions, risk tolerance, or completion criteria.

## Start here

- Read [`shared/INTERFACE_CONTRACT.md`](shared/INTERFACE_CONTRACT.md).
- Use the machine-readable shared laws in `shared/OWNERSHIP_MATRIX.yaml`, `STATE_MODEL.yaml`, `AUTHORIZATION_MODEL.yaml`, `EVIDENCE_MODEL.yaml`, `ERROR_TAXONOMY.yaml`, and `HANDOFF_PROTOCOL.yaml`.
- Instantiate the pair with `python scripts/instantiate_pair.py --help`.
- Validate the distribution with `python scripts/validate_pair.py . --mode template`.
- Read each sibling's `README.md` and `RUNBOOK.md` before operating it.

## Package status

- Contract family: `program-execution-system.v2`
- Blueprint contract: `program-execution-blueprint.v2`
- Controller contract: `program-execution-controller.v2`
- Compatibility: exact major-version match
- Remote mutation: denied unless a separately installed adapter and exact approval authorize the named action

## Learned lessons (implemented in pack)

Ledger: [`LEARNED_LESSONS.md`](LEARNED_LESSONS.md). LL-001–004 are encoded in Phase 0, gates, waivers, DoD, stop taxonomy, evidence, and ERROR_TAXONOMY (promoted to `environment/program-execution/core/`).

- **LL-001** — non-true-blocking CI demotion / waiver before major program
- **LL-002** — Phase 0 user-config; max autonomy within ceiling when deploying
- **LL-003** — local `make pr` required before push/PR; remediation exceptional
- **LL-004** — pre-start `uv.lock` / pin alignment

Autonomy bridge: `program-execution-controller-template/references/AUTONOMY_BRIDGE.md`.