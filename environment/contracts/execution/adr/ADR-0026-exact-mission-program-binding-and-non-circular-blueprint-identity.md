# ADR-0026: Mission Program Binding Is Exact-State and Must Not Create Circular Blueprint Identity

* Status: Accepted
* Date: 2026-08-28
* Decision owner: L9 architecture

## Context

A Program claiming Mission membership must preserve the exact Mission authority
and Blueprint identity under which it was admitted.

The final Mission Program Binding must reference `blueprint_digest`. If that
binding were itself included in the content covered by `blueprint_digest`,
Blueprint identity would become circular.

## Decision

A Mission Program Binding is an immutable relationship between one exact
Mission Revision and one exact Program / Blueprint identity.

It binds at minimum:

* binding ID;
* Mission ID;
* Mission revision;
* Mission digest;
* Program ID;
* Blueprint digest;
* binding time.

Historical Programs remain bound to the Mission Revision under which they were
admitted, even after Mission supersession. A new Program requires a new
binding.

The Controller receives only a read-only projection of the pinned Mission
binding. It cannot mutate the binding, rebind the Program, change Mission
revision, resolve a newer Mission Revision to alter locked authority, or issue
the Mission verdict.

The final Mission Program Binding is created only after the Blueprint has an
identity and remains outside the content domain covered by the Blueprint
digest it references.

Prohibited shape:

```text
Blueprint digest
    covers MISSION_BINDING.yaml
        contains blueprint_digest
```

Required identity order:

```text
Mission Revision
      ↓
Program Intent
      ↓
Intent Resolver
      ↓
Blueprint
      ↓
compute blueprint_digest
      ↓
Mission Program Binding
      ↓
Program Lock
      ↓
Controller
```

A future Blueprint may contain a non-circular Mission context projection with
already-known Mission ID, revision, and digest. The final Mission Program
Binding remains distinct.

## Constraints

* Binding is immutable.
* Mission digest cannot be caller-spoofed.
* Controller never resolves mutable live Mission state for a locked Program.
* Historical bindings survive Mission supersession unchanged.

## Consequences

Program provenance remains reproducible across Mission revisions and Blueprint
evolution. Blueprint identity remains acyclic.

## Rejected alternatives

### Store final Mission Program Binding inside Blueprint digest domain

Rejected because the binding contains `blueprint_digest`, creating circular
identity.

### Dynamically rebind Program to current Mission revision

Rejected because it silently changes locked Program meaning and authority.

## Related

* ADR-0011 — Autonomous replanning is bounded by immutable Program Lock
* ADR-0024 — Mission parent intent and Controller boundary
* ADR-0025 — Mission Revision immutability
