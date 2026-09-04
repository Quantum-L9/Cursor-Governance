<!-- L9_META
l9_schema: 1
parent: l9-idea-execute
layer: reference
role: architecture
tags: [ideaos, execution, topology, routing]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-09-02
/L9_META -->

# Architecture

## Table of contents

1. Authority stack
2. Single ingress
3. Execution topology
4. Atomic execution units
5. Owner versus executor
6. Specialized factories
7. Planning reuse
8. Concurrency
9. Authority
10. Resume and invalidation
11. Non-expansion rules

## 1. Authority stack

Preserve this order:

1. current user intent and explicit overrides;
2. validated IdeaOS decision and its source-authority/supersession model;
3. current authoritative downstream owner contract;
4. current repository state and repo-local law;
5. execution artifacts validated against the above;
6. older plans, examples, or historical evidence.

Idea Execute does not outrank any downstream owner inside that owner's domain.

## 2. Single ingress

Normalize accepted IdeaOS execution semantics into one Idea Execution Envelope. After acceptance, route from the envelope. Treat the raw pack as cited evidence unless an explicit change invalidates the envelope.

Do not let each adapter independently reinterpret the original pack.

## 3. Execution topology

Classify by the requested outcome and existing ownership, not by a preferred tool.

### NEW_PRODUCT_REPOSITORY

Use when a standalone new product/system repository is required and no specialized factory owns its creation.

### SPECIALIZED_FACTORY

Use when an existing factory owns the artifact lifecycle. A factory may internally provision repositories without routing through Foundry.

### EXISTING_REPO_CHANGE

Use for bounded work in one existing repository without cross-repository convergence requirements.

### EXISTING_SYSTEM_CAMPAIGN

Use when multiple existing repositories/owners participate in one causal program, or when cross-repository joins, shared acceptance, rollback, or terminal convergence make the work atomic.

## 4. Atomic execution units

An execution unit is the smallest body of work that can be handed to one owner without losing required semantics.

Do not split a unit merely because:

- one executor cannot currently represent it;
- separate repositories are involved;
- parallel execution would appear faster.

Split only when the units are semantically independent or connected by explicit output-to-input dependencies that downstream owners can honor independently.

## 5. Owner versus executor

Record both where needed:

- **runtime/artifact owner**: the repository or factory that permanently owns the capability;
- **execution adapter**: the mechanism that performs the current requested change.

Program Execution modifying PR_Repair does not make Program Execution the owner of PR repair semantics.

## 6. Specialized factories

Resolve specialized owners before generic routes.

Demonstrated initial owner:

- `website` -> `Quantum-L9/Website-Bot`.

A website requirement should not also produce a generic `product_repository` requirement for the Website-Bot-generated site repository. The factory owns that implementation detail.

## 7. Planning reuse

Evaluate readiness before invoking planning.

Use this ladder:

```text
raw idea -> IdeaOS required
validated decision, no execution plan -> planning may be required
valid implementation plan -> reuse
valid execution-ready contracts + deps + gates -> hand directly to compatible executor intake
```

If the selected executor requires a canonical projection of an already-valid plan, compile that projection without reopening the design.

## 8. Concurrency

Dependencies determine order.

Independent example:

```text
new product repo ----\
                      > run concurrently
marketing website ---/
```

Dependent example:

```text
product identity -> website authoring projection -> Website-Bot
```

Never use concurrency to bypass shared authority or atomic campaign semantics.

## 9. Authority

Attach authority to each execution unit and protected transition.

Local code realization does not imply:

- remote repository creation;
- push;
- PR publication;
- merge;
- production deployment;
- protected business/legal action.

Respect downstream owner's narrower authority even when the user grants broader intent elsewhere.

## 10. Resume and invalidation

A completed unit is reusable only when:

- its governing requirement is unchanged;
- upstream dependency outputs it consumed are unchanged;
- target repository state still satisfies its receipt assumptions;
- the adapter contract has not changed in a way that invalidates the handoff;
- its canonical downstream receipt/state remains valid.

Invalidate the earliest affected unit and its dependency cone.

## 11. Non-expansion rules

Do not add a new capability owner to the registry until a real consumer exists.

Do not create a generic abstraction solely to make the graph look complete.

Prefer, in order:

1. reuse an existing owner;
2. strengthen an existing boundary;
3. add a narrow adapter;
4. automate a repeated deterministic operation;
5. add a new abstraction only when recurring value is demonstrated.
