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

## What Mission is, and is not

Mission owns durable objective identity, Mission Acceptance Criteria, Mission
acceptance authority, target/scope ceilings, authorization ceilings, aggregate
resource ceilings, termination conditions, and cross-Program continuity.

Mission is **not** an Execution Program, Blueprint, Program Lock, Controller,
Task Card, Runtime Task, scheduler, worker, lease authority, provider, or agent
conversation. It declares **outcomes and ceilings** and never prescribes Task
Cards, waves, worktrees, files to edit, worker prompts, leases, provider
bindings, execution profiles, or runtime task state — those are structurally
rejected, in `metadata` as well as at the top level.

### Mission versus Program

A Program is one bounded, executable undertaking with a Blueprint, a Program
Lock, and a Controller that owns its runtime. A Mission is the objective those
Programs serve. One Mission may admit many Programs; a Program belongs to
exactly one Mission Revision, pinned at admission.

## Immutable revision, separate lifecycle

A **Mission Revision** is an immutable, digest-bound contract. Changing
authoritative semantics — `mission_owner` included — creates a *superseding*
revision rather than rewriting an existing one, so history stays append-only and
a Program's provenance stays reproducible.

**Mission Lifecycle State** is mutable status *concerning* a revision. The two
are different objects and must not be collapsed: embedding lifecycle in the
definition would let the same revision change meaning over time.

```text
PROPOSED  -> ACTIVE | CANCELLED | SUPERSEDED
ACTIVE    -> WAITING | SATISFIED | FAILED | CANCELLED | SUPERSEDED
WAITING   -> ACTIVE | SATISFIED | FAILED | CANCELLED | SUPERSEDED
SATISFIED -> []   FAILED -> []   CANCELLED -> []   SUPERSEDED -> []
```

`INCONCLUSIVE` does not imply a terminal state, and `NOT_SATISFIED` alone does
not imply `FAILED`. Mission cancellation or supersession never directly mutates
an already locked Program runtime.

`mission_digest` is SHA-256 over deterministic sorted JSON of the eleven
authoritative fields. `metadata` is excluded and cannot change authorization,
scope, acceptance, budgets, termination, or ownership — so it cannot change
identity either. The parsed object is transitively immutable: a retained
reference to `authority_ceiling` cannot flip `push` to `true`.

## Binding

A **Mission Program Binding** pins one exact Mission Revision to one exact
Program and Blueprint digest. Bindings are immutable; a new Program requires a
new binding, and supersession never rebinds an existing one. The Controller
receives a read-only projection of `mission_id`, `mission_revision`,
`mission_digest`, and `binding_id` — and may not mutate the binding, rebind the
Program, change the revision, or declare a Mission verdict.

### Why the Blueprint digest cannot reference back

The binding names `blueprint_digest`, so it must live **outside** the content
that digest covers. A `MISSION_BINDING.yaml` stored inside the Blueprint it
hashes would make the Blueprint's identity depend on a document that names that
identity. Hence the ordering:

```text
Mission Revision → Mission Admission Context → Program Intent → Intent Resolver
  → Blueprint → official validation → compute blueprint_digest
  → Mission Program Binding → Program Lock → Controller
```

### What `blueprint_digest` is, exactly

```text
blueprint_digest = lowercase_hex(SHA-256(exact bytes of MANIFEST.yaml))
```

The canonical input is the **exact bytes** of the instantiated Blueprint's final
`MANIFEST.yaml` — nothing is parsed, normalized, key-sorted, rewritten, or
reserialized first. That is what makes the digest name one exact Blueprint
rather than an equivalence class of them: two byte-different manifests that
happen to parse equal are two different Blueprints, and a binding that could not
tell them apart would no longer pin exact state.

Hashing the manifest rather than walking the tree keeps a single owner. The
official template manifest writer
(`../core/program-execution-blueprint-template/scripts/instantiate.py`) already
records every other Blueprint file with its SHA-256, so the manifest's bytes
transitively cover the Blueprint. Program Execution does not maintain a second
file inventory.

Two orderings are load-bearing:

* **Validation precedes identity.** The digest is computed only after the
  official instantiated-Blueprint validator reports the Blueprint valid. An
  invalid Blueprint has no admissible identity, so there is nothing for a
  binding to pin.
* **Any Mission context inside the Blueprint precedes the manifest.** A
  non-circular Mission context projection — already-known Mission ID, revision,
  and digest, and nothing else — may live in the Blueprint, but it must be
  written before the manifest is finalized so its bytes participate in identity.
  The *final* Mission Program Binding may not: it contains `blueprint_digest`.

Identity fails closed. A missing, non-regular, or unreadable `MANIFEST.yaml`
raises rather than returning a digest, because a well-formed digest for a
Blueprint that does not exist is the one failure a binding cannot detect. The
single implementation is
[`../core/shared/blueprint_identity.py`](../core/shared/blueprint_identity.py).

## Mission acceptance versus Program acceptance

Program convergence is *evidence toward* Mission acceptance. It is not Mission
acceptance. `Program CONVERGED`, `Program ACCEPTED`, `Task COMPLETED`, local
verification, and a worker's own claim are each explicitly non-implications.

Criterion results are `UNSATISFIED`, `PARTIALLY_SATISFIED`, `SATISFIED`,
`WAIVED`, `BLOCKED`, or `UNKNOWN`; only `SATISFIED` passes unconditionally and
`UNKNOWN` is non-passing. Mission verdicts are `SATISFIED`, `NOT_SATISFIED`,
`INCONCLUSIVE`, or `CANCELLED`, owned by `mission_owner`; a Controller
recommendation is advisory. Results and verdicts bind `mission_digest`, so a
result cannot drift onto a different revision. Mission evidence extends the
existing Program Execution evidence plane — it does not fork one.

## Monotonically narrowing authorization

`authority_ceiling` is a total map over the existing ten Program Execution
actions, and it is a ceiling, not an instruction. Effective Program
authorization is the intersection of:

```text
applicable safety/legal/security/organizational rules
AND exact action approval when required
AND Mission authority ceiling
AND Blueprint authorization ceiling
AND Controller policy
AND Source Contract request
AND Rendered Contract exact-state binding
```

Every lower layer may narrow and none may widen. Capability, credential,
connector, or provider availability is never authorization, and the Mission
ceiling grants no new remote mutation authority.

## Aggregate budgets

`max_model_cost_usd`, `max_agent_tokens`, `max_gate_calls`,
`max_duration_seconds`, and `max_parallel_programs` are ceilings over the
**whole Mission**, alongside `constraints.max_programs`. An individual Program
Controller must not claim independent authority to enforce Mission-wide totals:

> Mission Admission determines whether another executable undertaking may exist.
> Program Controller determines how an admitted undertaking executes.

The admission ledger that would enforce those totals is **not built here**.
Likewise, Mission v1 scope is declarative: Program Execution has no machine
defined selector grammar yet, so this claims no semantic Blueprint-subset
checking.

## Why there is no Mission Controller

Program Execution already owns scheduling, leases, retries, Runtime Task state,
and execution advancement. Giving Mission its own controller would create a
second execution-control plane and pull cross-Program objective authority into
the runtime. Cross-Program accounting belongs to a later Mission Admission
layer, not to a Mission Controller.

Runtime integration is deferred for the same reason: the Controller must
eventually consume only the Mission projection pinned into Program Lock, and
must never resolve mutable live Mission state to change locked execution
authority. Building that consumption before the contract surface exists would
bake in the wrong direction.

## Files

| Path | Role |
|---|---|
| `MISSION_MODEL.yaml` | Definition law, ownership, lifecycle domain, digest coverage |
| `MISSION_AUTHORITY_MODEL.yaml` | Ceiling, intersection, scope, budgets, termination |
| `MISSION_PROGRAM_BINDING.yaml` | Binding law and non-circular ordering |
| `MISSION_ACCEPTANCE_MODEL.yaml` | Criterion results, verdicts, evidence integration |
| `schemas/mission.schema.json` | Draft 2020-12 Mission Revision schema |
| `schemas/mission-program-binding.schema.json` | Draft 2020-12 binding schema |
| `mission.py` | Parser, digest, transitive immutability |
| `binding.py` | Immutable binding built from a parsed Mission |
| `../core/shared/blueprint_identity.py` | Exact-byte Blueprint identity (one owner, provider-neutral) |
| `tests/` | Executable law; fixtures for a conforming and a prescribing Mission |

`authority_ceiling` is a `$ref` to `program-execution-system/action-authorization.v2`
rather than a restatement of the ten actions, so the vocabulary keeps exactly one
owner. Validation builds a `referencing` registry over `../core/shared/schemas/`
(`schema_registry()` in `mission.py`). `date-time` is validated by a
`FormatChecker` this module registers itself — `jsonschema` treats an unknown
format as valid, so declaring the format without that registration would claim a
check that never runs.

## Future integration order — named, not built

```text
Mission → Mission Admission → Program Intent → Intent Resolver → Blueprint
  → compute blueprint_digest → Mission Program Binding → Program Lock → Controller
```

Not implemented here: Mission → Program Admission, Mission context → Program
Intent, Mission Program Binding *creation* inside the compiler, and Program Lock
immutable import. Blueprint identity **is** implemented, in
`../core/shared/blueprint_identity.py`. There is no Mission Controller,
Scheduler, Lease, Work Item, Task State, Worker, or Runtime Task; no
Mission-to-Program compilation; no `make campaign` wiring; and no change to the
campaign classifier or Controller runtime behaviour.
