---
name: l9-wire-into-repo
description: wire, rewire, verify, or unwire an existing repository artifact or capability by locating its authoritative owner, selecting the highest-leverage upstream integration point, propagating through existing manifests, generators, exports, adapters, and discovery surfaces, and proving downstream reachability. use when something exists but is not discoverable, reachable, registered, exported, invoked, configured, hooked up, or consistently consumed across intended repository surfaces.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, wiring, integration, discovery, reachability, upstream-leverage]
  owner: igor_beylin
  status: active
  version: 3.0.0
  updated: 2026-08-31
---

# Wire Into Repo (L9)

## Purpose

Wire existing repository artifacts and capabilities into the surfaces that need
them, at the highest valid authoritative point.

This skill owns generic repository integration topology. It does **not** own
implementation of the capability being wired.

A target is not fully wired because one consumer can see it. Wiring is complete
when every intended consumer is reachable from an authoritative source through
the repo's real propagation mechanisms, without unnecessary duplicate wiring.

## Governing invariant

> Never repair a downstream leaf when a valid authoritative upstream point can
> propagate the same integration to that leaf.

Wire source-first and outward:

```
authoritative owner → source registration/export → projector/reconciler → adapter/binding → consumer
```

Do not reverse ownership merely because a downstream file is easier to edit.

"Upstream" means dependency and authority upstream, not filesystem depth.

## Modes

| Mode | Outcome |
|------|---------|
| `wire` | Establish missing authoritative integration edges |
| `rewire` | Move existing integration to a higher valid owner and remove superseded downstream duplication |
| `verify` | Read-only proof of authority, propagation, and intended-consumer reachability |
| `unwire` | Remove integration edges in reverse dependency order and apply the target owner's lifecycle law |

Infer the mode from explicit user intent and observed repository state.

## Activation boundary

Use this skill when an artifact or capability **already exists** but needs to be
registered, exported, exposed, connected, discovered, invoked, configured,
hooked up, made reachable, rewired, verified, deregistered, or unwired.

Typical targets include skills, rules, policies, commands, hooks, libraries,
modules, public exports, schemas, configuration, manifests, registries,
plugins, adapters, generated projections, and real discovery indexes.

Do **not** use this skill to invent or implement the capability itself.

Do **not** use it for an ordinary isolated code import when no repository
integration topology changes.

When a narrower skill is the exact owner of the requested mutation, preserve
that ownership. This skill may establish the cross-surface topology and
delegate the specialized mutation; it must not duplicate the specialist's
implementation contract.

If the target does not yet exist, route to its creator or implementation owner.
For a new skill pack, use `l9-skill-compiler` first.

## Authority order

1. Explicit user outcome, target, intended consumers, and scope.
2. Repository canonical law, invariants, and ownership contracts.
3. The target capability's authoritative source or implementation owner.
4. Source manifests, registries, exports, generators, reconcilers, or installers.
5. Exact specialized skill or subsystem contract.
6. Existing downstream bindings and consumers.
7. This skill's references.
8. `Unknown` when authority or propagation cannot be proven.

A generated projection never outranks its source.

A dependent adapter never outranks the shared implementation owner.

Historical or archived files never become live authority merely because they
contain a matching name.

## Mandatory protocol

### 1. Bind the outcome

Record:

| Field | Meaning |
|-------|---------|
| `target` | Existing artifact or capability being wired |
| `mode` | `wire`, `rewire`, `verify`, or `unwire` |
| `intended-consumers` | Surfaces that must be able to discover, reach, invoke, or consume it |
| `required-outcome` | What "wired" means behaviorally |
| `scope` | Repository/task boundary that must not be crossed |

Infer observable values from the repository before treating them as unknown.

Do not require skill-specific fields for non-skill targets.

### 2. Inventory the live topology

Search outward from the target **and** inward from every intended consumer.

Classify each relevant node as one of:

- authoritative owner/source
- source manifest/registry/export
- generator/projector/reconciler/installer
- adapter/binding
- consumer
- generated derivative
- documentation/index
- historical/archive

Do not stop at the first matching reference. Trace references until ownership
and propagation are known.

Load [references/wiring-model.md](references/wiring-model.md) for the topology model.

### 3. Select the Upstream Leverage Point

For each intended consumer, trace the path upstream toward authority.

A candidate Upstream Leverage Point (ULP) must:

- own the relevant integration concern;
- be mutable within the requested scope;
- propagate to at least one intended consumer;
- preserve the requested semantics.

Reject a candidate when it is:

- a generated derivative with an identifiable source;
- a dependent adapter when a shared owner exists upstream;
- historical or archived;
- documentation-only for a behavioral integration;
- outside scope;
- broad enough to change unintended consumers or semantics.

Prefer candidates in this order:

1. stronger semantic authority;
2. greater intended-consumer coverage;
3. reuse of an existing propagation mechanism;
4. adapter/provider neutrality;
5. fewer direct writes;
6. less duplicated integration state.

Keep climbing until the next upstream node no longer owns the concern, crosses
scope, or would broaden behavior beyond the requested outcome.

If no single ULP covers all intended consumers, select the **minimum set** of
valid ULPs whose propagation closures cover them.

### 4. Build the minimum edge plan

Plan only the integration edges necessary to make the intended consumers
reachable.

Prefer:

```
source change + existing propagation
```

over:

```
N independent consumer edits
```

Do not create a new registry, adapter, manifest, index, or synchronization
mechanism merely because this skill expects one.

Reuse the repository's existing authority and propagation topology.

### 5. Mutate source-first

For `wire` and `rewire`:

1. Modify the authoritative ULP first.
2. Run the existing generator, projector, reconciler, installer, or sync path
   when the repository defines one.
3. Add direct leaf bindings only for consumers that cannot be reached by the
   authoritative propagation path.
4. In `rewire`, remove superseded downstream copies, rows, imports, bindings,
   or registrations **after** the upstream path is established.

Never hand-edit a generated derivative when its source or generator exists.

Never make documentation the only functional wiring change.

### 6. Preserve specialized ownership

When an intended edge is owned by a narrower subsystem or skill:

1. keep this skill responsible for topology and end-to-end closure;
2. use the specialized owner for its mutation contract;
3. resume generic reachability validation afterward.

The existence of a specialized owner is not permission to duplicate its logic
here.

### 7. Validate end-to-end

Load [references/validation-unwire.md](references/validation-unwire.md).

Prove:

- the target has one semantic owner for this concern;
- each intended consumer has a live reachability path;
- generated or projected surfaces derive from their source;
- no unnecessary duplicate leaf wiring remains;
- no dependent adapter became the shared implementation owner;
- historical files are not being mistaken for active surfaces.

`verify` performs these checks without mutation.

Do not report PASS when a mandatory authority or propagation edge is `Unknown`.

### 8. Report receipts

| Receipt | Value |
|---------|-------|
| Target | artifact/capability |
| Mode | `wire` / `rewire` / `verify` / `unwire` |
| Intended consumers | explicit consumer set |
| Authoritative owner | file/subsystem |
| ULP(s) | highest valid integration point(s) |
| Source edges changed | authoritative mutations |
| Propagation used | generator/projector/reconciler/export path |
| Leaf bindings | only irreducible direct bindings |
| Duplicates removed | rewiring cleanup |
| Validation | Passed / Failed / Unknown / NotApplicable |
| Residuals | non-blocking historical or informational references |

A file diff is not proof of wiring. The receipt must explain the
source-to-consumer path.

## Artifact archetypes

| Target class | Start upstream |
|--------------|----------------|
| Skill | Skill pack + authoritative routing/autonomy source |
| Rule/policy | Canonical rule/policy owner before projections |
| Command/entrypoint | Live command source and its registry/generator |
| Hook/lifecycle integration | Shared hook implementation/registry before surface bindings |
| Module/library/tool | Public export, package boundary, or canonical component registry |
| Configuration/schema/contract | Source schema or manifest before generated/configured consumers |
| Plugin/adapter | Shared capability first, thin surface binding second |
| Generated artifact | Generator or source manifest only |
| Documentation/index | Functional owner first; docs only when the index is itself a real discovery surface |

These are archetypes, not mandatory paths. Repository evidence decides the
actual owner.

## Unwire

Unwire is not "archive everything."

Remove integration in reverse topology:

```
consumer-only binding → source registration/export → regenerate/reconcile → target lifecycle action
```

The final target action is owned by the target's lifecycle contract.

A skill may require archival under `skills/_archived/`; a module, rule,
configuration file, hook, or adapter may have a different retirement contract.

Load [references/validation-unwire.md](references/validation-unwire.md) before unwiring.

## Hard prohibitions

Do not:

- wire leaf-first when a valid upstream owner can propagate;
- hand-edit generated projections when their source exists;
- duplicate a shared implementation under multiple adapters;
- invent registries or adapters without repository evidence;
- treat grep hits as proof of active wiring;
- treat documentation as behavioral reachability;
- restore archived machinery merely because a live reference is stale;
- leave obsolete downstream wiring after a successful rewire;
- claim PASS with an unresolved mandatory owner or consumer path.

## Resource Map

- [references/wiring-model.md](references/wiring-model.md) — authority graph, ULP selection, propagation, artifact archetypes, and specialized-owner boundaries.
- [references/validation-unwire.md](references/validation-unwire.md) — reachability proof, rewiring cleanup, unwire ordering, and lifecycle-specific retirement.
- Repository canonical law and invariants — always outrank this skill.

## Daisy-chain contract

| Owner | When |
|-------|------|
| `l9-skill-compiler` | Target is a skill that must first be created or structurally repaired |
| Exact specialized skill | A narrower skill owns one required mutation |
| `l9-update-agent-docs` | Functional wiring is complete and existing agent-facing pointers became stale |

Documentation refresh is conditional downstream work, not a prerequisite for
functional wiring.
