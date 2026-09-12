<!-- L9_META
l9_schema: 1
parent: l9-idea-execute
layer: reference
role: architecture
tags: [ideaos, execution, topology, routing, lineage]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-09-11
/L9_META -->

# Architecture

## Table of contents

1. Authority stack
2. Single ingress
3. Derived-artifact lineage
4. Execution topology
5. Atomic execution units
6. Owner versus executor
7. Planning reuse
8. Adapter evidence
9. Authority
10. Resume and invalidation
11. Non-expansion rules

## 1. Authority stack

Preserve this order:

1. current user intent and explicit overrides;
2. validated IdeaOS decision and source-authority/supersession model;
3. current authoritative downstream owner contract;
4. current repository state and repo-local law;
5. execution artifacts whose parent bindings validate against the above;
6. older plans, examples, or historical evidence.

Idea Execute does not outrank a downstream owner inside that owner's domain.

## 2. Single ingress

Normalize accepted execution semantics into one Idea Execution Envelope. After acceptance, route from the Envelope. Treat the raw pack as cited evidence unless an explicit change invalidates the Envelope.

Do not let each adapter reinterpret the raw idea independently.

## 3. Derived-artifact lineage

A derived artifact is never current merely because its schema validates.

```text
IdeaOS authority
  -> Envelope
  -> Graph
  -> Adapter Snapshot
  -> owner-native handoff
  -> owner receipt/state
  -> Idea Execution Receipt
```

The Graph binds to the exact semantic Envelope digest. Adapter snapshots bind to exact repository revisions/paths. The Idea Execution Receipt binds to both Envelope and Graph.

On rerun, validate bindings before reuse. See `artifact-reconciliation.md`.

## 4. Execution topology

Classify by requested outcome and existing ownership, not preferred tooling.

- `NEW_PRODUCT_REPOSITORY`: standalone new product/system repository and no specialized factory owns creation.
- `SPECIALIZED_FACTORY`: an existing factory owns the artifact lifecycle.
- `EXISTING_REPO_CHANGE`: bounded work in one existing repository without cross-repository convergence.
- `EXISTING_SYSTEM_CAMPAIGN`: multiple existing repositories participate in one causal program or shared convergence makes the work atomic.

A `cross_repository: true` declaration with fewer than two distinct repository-change targets is invalid evidence, not a campaign.

## 5. Atomic execution units

An execution unit is the smallest body of work that can be handed to one owner without losing semantics.

Do not split a unit merely because one executor cannot currently represent it, multiple repositories are involved, or parallel execution looks faster.

Split only when units are semantically independent or connected by explicit output-to-input dependencies downstream owners can honor independently.

## 6. Owner versus executor

Record both:

- runtime/artifact owner: who permanently owns the capability;
- execution adapter: the mechanism performing the requested change.

An execution adapter never becomes the semantic owner merely by modifying an owner's repository.

## 7. Planning reuse

Use this ladder:

```text
raw idea -> IdeaOS required
validated decision, no sufficient plan -> planning may be required
valid implementation plan -> reuse
valid execution-ready contracts + deps + gates -> hand directly to compatible executor intake
```

Reuse means **current and independently bound**. A stale plan or handoff reference is history, not authority.

For bounded existing-repo changes, `l9-plan-simple` is conditional. If an existing valid plan is sufficient for the executor, do not re-plan ceremonially.

## 8. Adapter evidence

Adapter contracts move. Discover them live and record a revision-bound capability snapshot.

Capability evaluation is three-state:

- proven support -> `COMPATIBLE`;
- proven non-support -> `EXECUTOR_CAPABILITY_GAP`;
- unresolved support -> `ADAPTER_CAPABILITY_UNKNOWN`.

Malformed or stale evidence is not executor incapability. Use `ADAPTER_SNAPSHOT_INVALID`, `ADAPTER_SNAPSHOT_STALE`, or `ADAPTER_CONTRACT_CONFLICT` as appropriate.

## 9. Authority

Attach authority to each execution unit and protected transition.

Local code realization does not imply remote repository creation, push, PR publication, merge, deployment, or protected business/legal action.

Never reuse publication/deployment authorization merely because local execution evidence remains reusable.

## 10. Resume and invalidation

A completed unit is reusable only when:

- its governing requirement is unchanged;
- upstream dependency outputs it consumed are unchanged;
- target repository state still satisfies its receipt assumptions;
- adapter source bindings remain current;
- its canonical downstream receipt/state remains valid.

Invalidate the earliest affected layer and its dependency cone, not unrelated siblings.

## 11. Non-expansion rules

Do not add a new capability owner until a real consumer exists. Do not create a generic abstraction merely to make the graph look complete.

Prefer, in order:

1. reuse an existing owner;
2. strengthen an existing boundary;
3. add a narrow adapter;
4. automate a repeated deterministic operation;
5. add a new abstraction only when recurring value is demonstrated.
