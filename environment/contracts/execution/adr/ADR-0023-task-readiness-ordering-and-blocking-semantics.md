# ADR-0023: Task Readiness, Ordering, and Blocking Semantics

- **Status:** Accepted
- **Date:** 2026-08-26
- **Decision owner:** L9 architecture

## Context

Program Execution has allowed lifecycle vocabulary such as `blocked`,
`pending`, `advisory`, and `awaiting approval` to appear where the actual
condition was execution ordering. A task whose definition is complete but
whose predecessor has not yet completed is not blocked: its definition is
ready, and its eligibility is constrained by the dependency graph.

Conflating definition readiness with execution eligibility produced concrete
failures: tasks compiled as `definition_status: blocked` became permanently
unclaimable because the controller has no `blocked → ready` definition
transition; the runtime initialized every complete task as `BLOCKED`; and
`pec next` reported every non-eligible task — including tasks merely waiting
on a predecessor — as blocked, so sequencing read as missing authorization.

## Decision

### 1. Complete task definitions MUST be `ready`

If a task definition contains sufficient information to be executed once its
prerequisites are satisfied, it MUST carry `definition_status: ready`. This
holds even while predecessor tasks are incomplete, its wave has not opened,
dependency edges are unsatisfied, or the scheduler cannot yet claim it.

### 2. Ordering is represented exclusively by graph semantics

Execution ordering MUST use `dependencies`, `dependency_edges`, `waves`, and
applicable gate relationships. These constructs are the ordering authority.
Ordering MUST NOT be represented by mutating definition readiness.

### 3. Readiness is not claimability

**READY ≠ CLAIMABLE.**

```
claimable =
    definition ready
    AND dependencies satisfied
    AND wave prerequisites satisfied
    AND required gates/evidence/authority satisfied
    AND no genuine blocker
```

Schedulers MUST derive claimability from the graph and runtime checks; they
MUST NOT interpret `ready` as permission to violate ordering.

### 4. Waiting is not blocked

A task waiting for a predecessor MUST remain definition-ready. Its condition
is `ready + not currently eligible` — reported as **waiting**, never as
**blocked**. The runtime MUST compute eligibility without mutating definition
readiness; a `blocked → ready` definition round-trip for ordinary ordering is
prohibited.

### 5. `blocked` is reserved for genuine inability to proceed

Blocking vocabulary is reserved for conditions under which execution cannot
validly continue, including at minimum:

- an unresolved blocking Unknown;
- an unresolved required authority or decision;
- a failed blocking gate;
- missing required evidence that execution genuinely needs first;
- a material semantic contradiction between authoritative requirements;
- a failed required validation;
- an integrity or authorization failure that makes execution invalid.

A blocking gate that has been evaluated and **failed** is a blocker. A future
gate that has simply not yet become satisfiable is a waiting prerequisite,
not a failed blocker. The same distinction applies to predecessor-wave exit
gates and current-wave entry gates. Evidence the runtime can collect itself
within existing authority MUST NOT create an artificial pre-execution block.

### 6. Forbidden ordering vocabulary

The following MUST NOT be used as task-ordering or ordinary-readiness
mechanisms:

- `definition_status: blocked`
- `pending`
- `advisory`
- `awaiting approval`
- `not approved`

Where such vocabulary remains for other domain-specific reasons (decision
lifecycle, gate results, business fields), it MUST NOT implicitly control
task execution ordering.

### 7. Backward compatibility

Legacy campaign source containing `definition_status: blocked` together with
a non-empty `dependencies` list MAY be canonicalized at the compiler
boundary, but newly generated source MUST NOT emit it, canonical Task Cards
MUST emit `ready`, and PEC MUST NOT expose the dependency wait as a real
blocker. `definition_status: blocked` with no dependency to wait on MUST
fail compilation instead of producing a permanently unclaimable task.

The legacy `BLOCKED` runtime state remains readable for persisted runtimes,
but it MUST NOT be the initialization state for a complete task: new complete
tasks initialize as `WAITING` (definition complete, prerequisites not yet
resolved into a claim) and move `WAITING → ELIGIBLE` when readiness passes.

## Runtime principle

Governance prevents invalid execution; it does not manufacture
administrative reasons to prevent valid work. If a task must run later,
express that through dependencies, edges, waves, or gates. If it is truly
impossible or invalid to proceed, identify the concrete blocker. `BLOCKED`
is an exceptional semantic condition, not a scheduling primitive.

## Consequences

- Definition state is stable; the dependency graph is the single ordering
  source of truth.
- `pec next` distinguishes `ready` / `waiting` / `blocked`; `blockers`
  output carries only genuine blocking reasons.
- `BLOCKED` becomes high-signal instead of routine noise.
- Controllers must explicitly distinguish readiness from claimability, and
  validators need blocker provenance — accepted costs of removing the
  ambiguity.

## Rejected alternatives

### Keep compiler normalization as the only fix

Rejected: normalizing `blocked + dependencies` to `ready` at the compiler
boundary repairs one producer path but leaves the runtime initializing
complete tasks as `BLOCKED` and reporting sequencing as blocked. The false
semantics must be corrected where they are produced and reported.

### Rename `blocked` to `waiting` everywhere

Rejected: a rename without classification would erase the genuine blocker
signal (unresolved Unknowns, failed gates, missing evidence) that `BLOCKED`
exists to carry.
