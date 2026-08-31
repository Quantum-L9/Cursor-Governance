<!-- L9_META
l9_schema: 1
parent: l9-wire-into-repo
layer: reference
role: wiring_model
tags: [wiring, topology, authority, upstream-leverage, reachability]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-31
/L9_META -->

# Repository Wiring Model

## Purpose

Model repository wiring as an authority-and-reachability graph so integration
changes land at the highest valid source instead of accumulating downstream
patches.

This model is artifact-neutral.

## Graph model

Represent the relevant repository topology as a directed graph:

```
G = (V, E)
```

Nodes are artifacts, ownership surfaces, propagation mechanisms, bindings, or
consumers.

Edges represent integration relationships.

The objective is not to maximize the number of edges. The objective is to
establish the smallest authoritative edge set whose propagation closure reaches
the intended consumers.

## Node classes

| Node class | Meaning | Ownership eligibility |
|------------|---------|----------------------|
| Authoritative owner/source | Implements or canonically defines the concern | Highest |
| Source manifest/registry/export | Canonically declares integration | High |
| Generator/projector/reconciler/installer | Propagates source state | Mechanism, usually not semantic owner |
| Adapter/binding | Connects shared capability to one surface | Leaf or near-leaf |
| Consumer | Discovers, imports, invokes, loads, or configures capability | Destination |
| Generated derivative | Materialized output of another source | Never owner when source exists |
| Documentation/index | Human/agent discovery description | Owner only when the index itself is the real control surface |
| Historical/archive | Retained inactive material | Never live owner |

## Edge classes

Common edges include:

| Edge | Example meaning |
|------|-----------------|
| registration | source registry declares target |
| export | public/package surface exposes implementation |
| discovery | consumer can locate target |
| projection | source state materializes elsewhere |
| binding | adapter connects target to a runtime |
| invocation | entrypoint reaches implementation |
| configuration | authoritative config activates target |
| installation | installer makes target available |
| lifecycle | source controls activation/deactivation |

The concrete repository may use different names. Classify by semantics, not
filename.

## Intended-consumer closure

Let `C` be the explicit set of intended consumers.

For candidate node `n`, define `closure(n)` as the consumers reachable through
the repository's existing propagation graph after changing `n`.

A candidate is useful only when:

```
closure(n) ∩ C != ∅
```

Do not optimize for unrelated consumers.

## Upstream Leverage Point

An **Upstream Leverage Point (ULP)** is the highest valid integration node from
which the requested outcome can propagate.

A ULP must satisfy all of:

1. It has semantic authority for the integration concern.
2. It is mutable within task scope.
3. Its propagation path is real and evidenced.
4. It reaches one or more intended consumers.
5. Changing it preserves the requested semantics.
6. Its fanout does not unintentionally alter consumers outside the requested
   outcome.

A filesystem parent is not automatically upstream.

A root-level file can be downstream of a nested manifest.

A generated file can be physically prominent while remaining semantically
downstream.

## Candidate exclusions

Never select as ULP:

- a generated derivative when a source exists;
- an adapter when a shared owner exists upstream;
- an archived or historical artifact;
- a documentation pointer for runtime behavior;
- a copied implementation whose upstream shared implementation is known;
- an external or protected owner outside the authorized scope;
- a source whose fanout would change unintended semantics.

## Selection order

Compare valid candidates lexicographically:

1. semantic authority;
2. intended-consumer coverage;
3. existing propagation reuse;
4. adapter/provider neutrality;
5. number of authoritative writes required;
6. duplicate state introduced;
7. long-term drift surface.

Authority beats convenience.

Do not select a weaker owner merely because editing it requires fewer commands.

## Upstream climb

For each intended consumer:

1. Start at the consumer.
2. Identify the binding or discovery edge that reaches the target.
3. Identify the source of that binding.
4. Continue through manifests, exports, generators, or shared owners.
5. Stop only when the next upstream node:
   - does not own this concern;
   - crosses explicit task scope;
   - is not mutable;
   - would change unintended semantics;
   - belongs to a narrower exact owner that must execute the mutation.

The last valid node before that stop is a ULP candidate.

## Minimum ULP set

A single ULP is preferred when its propagation closure covers all intended
consumers.

When no single valid owner covers the entire set, choose the smallest set
`U = {u1 ... un}` such that:

```
C ⊆ closure(u1) ∪ ... ∪ closure(un)
```

The resulting ULPs should form the minimum necessary authoritative frontier.

Do not manufacture a synthetic common registry solely to force a one-node
solution.

## Mutation order

For `wire`:

```
owner/source → propagation mechanism → irreducible leaf binding → validation
```

For `rewire`:

```
new upstream source → propagation → validate new path → remove superseded leaf wiring → validate again
```

Never remove an old working leaf before the new upstream path has been proven.

## One semantic owner

Multiple physical projections are acceptable.

Multiple semantic owners are not.

Healthy:

```
one manifest → generated registry A + generated registry B
```

Unhealthy:

```
registry A manually maintained + registry B manually maintained
```

when both independently encode the same authority.

A projection is allowed to translate or narrow source state for its surface.
It must not silently become an independent brain.

## Artifact-specific starting heuristics

### Skills

Start at the live skill pack and the repository's authoritative skill-routing
or autonomy source.

Generated registries and adapter projections are downstream.

For L9 governance, treat the authoritative autonomy/routing source as input to
generated skill-registry and adapter reconciliation; do not hand-maintain the
generated registry as a peer owner.

### Rules and policy

Find the canonical rule or policy owner.

If adapters or runtime-specific rule files are generated or projected from that
owner, change the owner and propagate.

Do not duplicate policy prose independently across surfaces.

### Commands and entrypoints

Distinguish a live entrypoint from archived or generated command indexes.

Change the live command source or authoritative command registry first.

Do not create a slash command merely because a skill exists. A Skill can remain
the only public activation surface when that is the intended architecture.

### Hooks and lifecycle behavior

Find the shared lifecycle implementation or hook registry first.

Adapter-specific hook files should bind to that shared capability rather than
owning separate copies.

### Code, tools, and modules

Look for the canonical public export, package boundary, dependency injection
registration, plugin registry, or component manifest.

Prefer one upstream export/registration over repeated direct consumer imports
when the capability is intentionally shared.

Do not force an upstream export when the target is intentionally private to one
consumer.

### Configuration, schemas, and contracts

Find the source manifest or schema that owns the value or structure.

Generated configurations and surface-specific translations remain downstream.

### Plugins and adapters

Implement or locate the shared capability first.

Then add the minimum surface binding.

Never put the shared brain under a dependent adapter merely because that
adapter was the first consumer.

### Generated artifacts

A generated artifact is a receipt of wiring, not the place to wire.

Locate its source and generator.

Modify the source, run the generator, and validate the derivative.

### Documentation

Documentation can be an intended consumer but normally is not functional
wiring.

Update docs after behavior is wired when an existing pointer became stale.

A docs-only change cannot prove runtime reachability.

## Specialized-owner precedence

Generic wiring orchestration does not erase domain ownership.

When a narrower skill or subsystem explicitly owns a required operation:

```
generic topology diagnosis → specialized mutation → generic closure validation
```

The narrower owner controls its local invariants.

The generic wiring skill controls whether the complete intended consumer set is
connected without duplicated ownership.

## No-invention rule

Do not create a new:

- registry;
- adapter;
- generator;
- reconciler;
- index;
- symlink topology;
- command layer;
- plugin layer

merely because one would make the wiring diagram look uniform.

Create a new integration surface only when repository authority or an explicit
architectural requirement makes that surface the correct owner.

## Evidence rule

A reference proves that two things mention each other.

It does not prove that one reaches the other.

Strong evidence includes:

- authoritative manifest/export state;
- deterministic generator output;
- import or load resolution;
- runtime discovery;
- executable validation;
- existing repository conformance checks;
- consumer-visible behavior.

Use the strongest evidence available for the target class.
