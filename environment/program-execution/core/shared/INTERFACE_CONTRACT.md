# Blueprint–Controller Interface Contract

## Contract identity

- Pair: `program-execution-system.v2`
- Blueprint: `program-execution-blueprint.v2`
- Controller: `program-execution-controller.v2`
- Compatibility rule: major versions must match exactly; minor versions may advance only when declared backward-compatible.

## Ownership matrix

| Concern | Canonical owner | Runtime projection | Update path |
|---|---|---|---|
| Program identity and target state | Blueprint | Program Lock | superseding Blueprint |
| Responsibility authority | Blueprint | read-only Program Lock projection | accepted decision + superseding Blueprint |
| Execution target identity | Blueprint | repository/adapter registration | reconcile exact current state |
| Task definition | Blueprint | runtime task projection | superseding task definition |
| Task runtime state | Controller | SQLite + ledger | validated state transition |
| Gate definition | Blueprint | runtime gate record | superseding gate definition |
| Gate evaluation | Controller | gate receipt + ledger | independent evaluation command |
| Decision result | Blueprint authority | read-only decision projection | accepted decision + Blueprint reseal |
| Unknown resolution | Blueprint authority | Controller blocker projection | evidence-backed resolution + Blueprint reseal |
| Authorization ceiling | Blueprint | Source/Rendered Contract subset | may only narrow at runtime |
| Action approval | Operator/approval authority | Controller approval receipt | exact, expiring approval |
| Attempt result | Worker claim only | Attempt Receipt | independent verification required |
| Verification verdict | Controller | Verification Receipt | rerun against exact state |
| Final program verdict | Program owner | Controller Handoff Receipt is advisory evidence | named acceptance decision |

## Import contract

The Controller imports all files listed in `EXECUTION_INDEX.yaml`, records SHA-256 for each, validates cross-file references, normalizes them into a Program Lock, and refuses advancement when any imported source changes.

## Authorization law

The effective permission for an action is the intersection of:

1. applicable safety, legal, security, and organizational rules;
2. latest exact action approval, when required;
3. Blueprint task authorization ceiling;
4. Controller policy;
5. Source Contract request;
6. Rendered Contract exact-state binding.

No lower layer may widen a higher layer.

## Evidence law

Every material advancement must cite an `EVIDENCE_CATALOG.yaml` record or a Controller-generated receipt with:

- stable evidence ID;
- artifact or source location;
- exact revision or digest;
- method and environment;
- producer and timestamp;
- result and scope;
- freshness or expiry;
- claims supported and contradicted.

## Handoff law

The Controller exports a `program-execution-controller.handoff-receipt.v2` document. It may report local task passes and gate evaluations, but it may not declare the program converged. The program owner accepts a terminal verdict through an explicit Blueprint decision or closure record.
