# Mission

Mission is durable parent intent above one or more Execution Programs.

```text
Mission
  │
  │ durable objective / acceptance / budget / continuity
  │
  ├────► Execution Program P1 ── Blueprint → Program Lock → Controller
  ├────► Execution Program P2 ── Blueprint → Program Lock → Controller
  └────► Execution Program Pn ── Blueprint → Program Lock → Controller
```

A Mission may survive multiple Programs. A Program Execution Controller never
becomes a Mission Controller.

Mission declares **outcomes and ceilings**. It never prescribes Task Cards,
Runtime Tasks, waves, worktrees, files to edit, worker prompts, leases,
provider bindings, execution profiles, or runtime task state.

## Authority

| Concern | Owner |
|---|---|
| Mission definition, Mission Revision, Mission verdict | `mission_owner` |
| Program runtime, Task runtime | Program Execution Controller |
| Final Program verdict | `program_owner` |

Mission authority is an **outer ceiling** in the existing authorization
intersection. Lower layers may narrow it and never widen it. Capability,
credential, connector, or provider availability is not authorization.

Decisions: [ADR-0024](../../contracts/execution/adr/ADR-0024-mission-parent-intent-and-controller-boundary.md),
[ADR-0025](../../contracts/execution/adr/ADR-0025-mission-revision-immutability-and-lifecycle-separation.md),
[ADR-0026](../../contracts/execution/adr/ADR-0026-exact-mission-program-binding-and-non-circular-blueprint-identity.md),
[ADR-0027](../../contracts/execution/adr/ADR-0027-mission-acceptance-separate-from-program-acceptance.md).

## Revision is not lifecycle

A **Mission Revision** is immutable contract identity. **Mission Lifecycle
State** is mutable status *concerning* that revision. They are different
objects and must not be collapsed — embedding lifecycle in the definition would
let the same revision change meaning over time and would undermine digest-bound
Program provenance.

```text
PROPOSED  -> ACTIVE | CANCELLED | SUPERSEDED
ACTIVE    -> WAITING | SATISFIED | FAILED | CANCELLED | SUPERSEDED
WAITING   -> ACTIVE | SATISFIED | FAILED | CANCELLED | SUPERSEDED
SATISFIED -> []   FAILED -> []   CANCELLED -> []   SUPERSEDED -> []
```

Changing authoritative Mission semantics — `mission_owner` included — creates a
superseding revision rather than rewriting an existing one. Mission
cancellation or supersession never directly mutates an already locked Program
runtime; existing Programs stay bound to the exact revision under which they
were admitted.

## Files

| Path | Role |
|---|---|
| `MISSION_MODEL.yaml` | Mission definition law, ownership, and the lifecycle state domain |
| `schemas/mission.schema.json` | Draft 2020-12 Mission Revision schema |
| `tests/test_mission.py` | Executable definition/boundary and lifecycle law |
| `tests/fixtures/` | One conforming Mission, one that prescribes execution |

`authority_ceiling` is a `$ref` to `program-execution-system/action-authorization.v2`
rather than a restatement of the ten actions, so the action vocabulary keeps
exactly one owner. Validating the Mission schema therefore needs a
`referencing` registry built from `../core/shared/schemas/` — see `_registry()`
in `tests/test_mission.py`.

## What is deliberately not here

This is the non-runtime foundation. There is no Mission Controller, Scheduler,
Lease, Work Item, Task State, Worker, or Runtime Task, no Mission-to-Program
compilation, no `make campaign` wiring, and no change to the campaign
classifier or to Controller runtime behavior.

Implemented so far: `MISSION_DEFINITION_BOUNDARY_CONTRACT` and
`MISSION_REVISION_LIFECYCLE_CONTRACT`. Still unimplemented, and listed under
`deferred_to_later_contracts` in `MISSION_MODEL.yaml`: the authority/scope/
budget/termination semantics, `mission_digest` and the deep-immutability parser
(`mission.py`), Mission Program Binding, and the Mission acceptance/evidence
model.
