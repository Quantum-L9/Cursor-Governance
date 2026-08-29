# ADR-0024: Mission Is Durable Parent Intent; the Program Controller Remains Runtime Authority

* Status: Accepted
* Date: 2026-08-28
* Decision owner: L9 architecture

## Context

Program Execution already separates goal-level intent from executable Program
authority and separates design-time Blueprint synthesis from mutable runtime
execution. Some objectives outlive one Program and require durable continuity
across successive or parallel Programs.

That continuity cannot safely exist only in agent context. It also cannot be
assigned to the Program Execution Controller without expanding the Controller
into a cross-Program authority plane.

## Decision

Introduce Mission as the durable parent contract above one or more Execution
Programs.

Mission owns durable objective identity, Mission Acceptance Criteria, Mission
acceptance authority, target/scope ceilings, authorization ceilings, aggregate
resource ceilings, termination conditions, and cross-Program continuity.

Mission is not an Execution Program, Blueprint, Program Lock, Program
Execution Controller, Task Card, Runtime Task, scheduler, worker, lease
authority, provider, or agent conversation.

Mission declares outcomes and ceilings. It does not prescribe Task Cards,
Runtime Tasks, waves, worktrees, files to edit, worker prompts, leases,
provider bindings, execution profiles, or runtime task state.

The eventual executable path is:

```text
Mission
  ↓
Mission Admission
  ↓
Program Intent
  ↓
Intent Resolver
  ↓
Blueprint
  ↓
Mission Program Binding
  ↓
Program Lock
  ↓
Program Execution Controller
```

Program intent resolution and Blueprint synthesis remain responsible for
turning authorized Mission scope into executable Program definition.

The Program Execution Controller remains the sole owner of mutable Program and
Runtime Task execution state.

Mission authority is an outer ceiling in the existing authorization
intersection. Lower layers may narrow but never widen it. Capability,
credential, connector, or provider availability is not authorization.

Mission budgets are Mission-wide admission ceilings, not Controller scheduling
state. Future cross-Program accounting belongs to Mission Admission/accounting,
not a Mission Controller.

The first Mission implementation is deliberately non-runtime.

## Constraints

* Runtime Task state remains Controller-owned.
* Final Program verdict remains program-owner-owned.
* Mission definition remains mission-owner-owned.
* Mission cannot issue Program task leases.
* Mission cannot directly mutate Program runtime.
* No new remote mutation authority is granted.
* No second execution-control plane may emerge.

## Consequences

Durable objectives can span multiple independently locked Programs without
transferring runtime authority upward. Program execution remains bounded by
existing runtime ownership. Cross-Program resource ceilings require a later
admission/accounting mechanism.

## Rejected alternatives

### Put Mission fields directly into each Blueprint

Rejected because it duplicates durable objective identity and makes
cross-Program continuity and supersession ambiguous.

### Let the Program Execution Controller own Mission lifecycle or acceptance

Rejected because it expands the Controller into cross-Program objective
authority.

### Add a Mission Controller, Mission Scheduler, or Mission Lease system

Rejected because existing Program Execution already owns scheduling, leases,
retries, Runtime Task state, and execution advancement.

### Compile Mission directly into Task Cards

Rejected because it bypasses Program intent resolution and Blueprint synthesis.

## Related

* ADR-0007 — Goal-level intent is the Program Execution front door
* ADR-0010 — Program synthesis emits design-time authority; Controller remains runtime authority
* ADR-0011 — Autonomous replanning is bounded by immutable Program Lock
* ADR-0025 — Mission Revision immutability and lifecycle separation
* ADR-0026 — Exact Mission Program Binding and non-circular Blueprint identity
* ADR-0027 — Mission acceptance is separate from Program acceptance
* `environment/program-execution/core/shared/OWNERSHIP_MATRIX.yaml`
* `environment/program-execution/core/shared/AUTHORIZATION_MODEL.yaml`
