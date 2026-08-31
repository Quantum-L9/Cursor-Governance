<!-- L9_META
l9_schema: 1
parent: l9-wire-into-repo
layer: reference
role: validation_and_unwire
tags: [wiring, validation, unwire, reachability, lifecycle]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-31
/L9_META -->

# Wiring Validation and Unwire

## Purpose

Prove that repository integration is authoritative, reachable, non-duplicative,
and reversible.

Validation is topology-aware. Presence of matching text is insufficient.

## Result states

Every applicable validation dimension must report one of:

```
Passed | Failed | Unknown | NotApplicable
```

Do not convert `Unknown` into `Passed`.

A mandatory `Unknown` blocks an overall PASS.

## Wire validation

### Identity

Prove that the target artifact or capability being wired is the intended
target.

For named or packaged artifacts, verify identity against the target's own
canonical metadata or implementation.

### Authority

Prove the selected ULP is authoritative for the integration concern.

Fail when the mutation was made only to:

- a generated derivative;
- a dependent adapter that should consume a shared owner;
- an archive;
- a documentation pointer for behavioral wiring;
- an arbitrary duplicate registry.

### Reachability

For every intended consumer, record a path:

```
authoritative owner → ... → consumer
```

Every intermediate edge must be supported by repository evidence.

Consumers may have different terminal bindings while sharing the same upstream
owner.

Fail when any intended consumer has no proven path.

### Propagation

When a generator, projector, reconciler, installer, or synchronization
mechanism exists:

1. prove the authoritative source was changed;
2. run or otherwise deterministically validate the propagation mechanism;
3. prove the expected derivative changed or remained correctly derived.

Do not hand-edit the derivative to manufacture a passing result.

### Ownership uniqueness

Prove there is one semantic owner for the integration concern.

Multiple derived representations are allowed.

Independent manually maintained representations of the same authority are a
failure unless repository law explicitly defines them as peers.

### Adapter direction

For shared capability, prove adapters consume the shared owner.

Fail if a supposedly shared implementation is owned by a dependent adapter and
upstream/core surfaces import it backward.

### Leaf minimization

Inspect direct consumer edits after propagation.

Each remaining direct leaf binding must be irreducible: the upstream
propagation mechanism cannot provide it.

A direct leaf edit that duplicates an upstream-derived edge is drift.

## Rewire validation

A rewire must prove both introduction and subtraction.

Before removing the old path:

1. establish the new upstream source;
2. propagate it;
3. prove all intended consumers remain reachable.

Then remove obsolete downstream registrations, copies, exports, imports,
bindings, or documentation claims.

Run the complete validation again after cleanup.

A rewire that leaves the old duplicate owner active is incomplete.

## Verify mode

`verify` is read-only.

It performs the same authority, reachability, propagation, ownership, adapter,
and leaf-minimization checks without mutation.

Verification should identify the highest valid ULP even when the existing
wiring currently lives downstream.

A result can therefore be behaviorally reachable but architecturally `Failed`
because it is wired from the wrong owner.

## Generic unwire model

Unwire removes reachability without corrupting unrelated ownership.

Do not assume that retirement means archival.

### 1. Inventory active edges

Identify:

- authoritative registrations or exports;
- generated/projected derivatives;
- direct leaf bindings;
- consumers;
- lifecycle rules for the target artifact class.

Separate active integration edges from historical references.

### 2. Determine retention intent

The target may be:

- disconnected but retained;
- superseded;
- disabled;
- archived;
- deleted.

Use the target owner's lifecycle contract.

Do not invent a universal retirement policy.

### 3. Remove irreducible leaf bindings

Remove consumer-local bindings that will not disappear automatically when the
authoritative source changes.

Do not remove generated derivatives by hand.

### 4. Remove the authoritative edge

Remove or disable the registration, export, manifest entry, configuration, or
other authoritative integration edge that makes the target active.

### 5. Propagate subtraction

Run the repository's existing generator, projector, reconciler, installer, or
sync mechanism.

Prove derived registrations and bindings disappear.

### 6. Apply target lifecycle

Only after active reachability has been removed, apply the target artifact's
own lifecycle rule.

Examples include archive, retain-disabled, supersede, or delete.

Historical references may remain when they are clearly non-activating.

### 7. Prove negative reachability

For every former intended consumer, prove there is no active path to the
retired integration.

Textual historical mentions do not fail negative reachability unless they still
participate in discovery, routing, invocation, configuration, or installation.

## Skill retirement special case

When the target is a governed Skill and repository law requires archived
retirement:

1. Set `metadata.status: deprecated`.
2. Set top-level `disable-model-invocation: true`.
3. Move the pack out of live `skills/` into the repository's skill archive
   convention, preserving history when required.
4. Remove active autonomy/routing tier entries.
5. Add the archived path to the repository's do-not-migrate/do-not-reconcile
   protection when that mechanism exists.
6. Regenerate skill registries and adapter projections from their authoritative
   sources.
7. Remove live preloads and activatable documentation pointers.
8. Prove the Skill is absent from all live discovery surfaces.

Do not add arbitrary top-level frontmatter keys such as `superseded_by` when
the skill schema does not permit them.

If replacement provenance is useful, record it only in a schema-valid metadata
location or non-frontmatter historical documentation.

Do not generically rename or delete `agents/openai.yaml`. Platform-packaging
metadata belongs to the skill compiler's packaging contract.

Skill archival is a specialization of unwire, not the definition of unwire.

## Failure conditions

Overall validation is `Failed` when any mandatory condition is true:

- an intended consumer is unreachable;
- the selected mutation surface is not authoritative;
- a generated output was edited as source;
- duplicate semantic owners remain;
- shared implementation ownership is inverted into an adapter;
- a rewire leaves superseded active wiring;
- an unwire leaves an active discovery/invocation path;
- reported propagation did not actually occur.

Overall validation is `Unknown` when a mandatory authority or edge cannot be
established from available evidence.

## Receipt

Report:

| Dimension | Result | Evidence |
|-----------|--------|----------|
| Target identity | state | source |
| Authoritative owner | state | source |
| ULP selection | state | rationale |
| Consumer reachability | state | path per consumer |
| Propagation | state | generator/reconciler/export evidence |
| Ownership uniqueness | state | duplicate search |
| Adapter direction | state | ownership path |
| Leaf minimization | state | remaining direct bindings |
| Rewire cleanup | state | removed obsolete edges |
| Unwire negative proof | state | former consumers |
| Overall | state | blocking failures/unknowns |

Do not report "wiring complete" or "unwire complete" without this evidence.
