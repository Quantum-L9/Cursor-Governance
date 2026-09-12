---
name: l9-idea-execute
description: route a validated IdeaOS decision or execution-ready idea pack into the shortest governed downstream owner, while independently validating derived-artifact lineage and live adapter capability evidence. use for new product repositories, specialized factories, bounded existing-repo changes, or multi-repo Program Execution campaigns after IdeaOS has decided outcomes. do not use for raw idea refinement, generic coding, or implied publication/merge/deployment authority.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, ideaos, execution, routing, lineage, foundry, website-bot, program-execution]
  owner: igor_beylin
  status: active
  version: 1.1.0
  updated: 2026-09-11
---

# L9 Idea Execute

## Purpose

Turn validated IdeaOS intent into governed downstream execution without becoming another planner, factory, coding runtime, or Program Execution engine.

Preserve:

```text
IdeaOS -> l9-idea-execute -> authoritative downstream owner -> owner-native receipt
```

IdeaOS decides **what outcomes are required**. This skill decides **which existing owner can satisfy each outcome and how to hand it off correctly**. The downstream owner decides **how to perform its work**.

## Core contract

| Input | Output | Scope |
|---|---|---|
| Validated IdeaOS decision or execution-ready pack | Envelope + Execution Graph + thin Receipt | Route, reconcile, and hand off only |

Load:

- `references/contracts.md`
- `references/architecture.md`
- `references/artifact-reconciliation.md` when supplied execution artifacts may be reused
- `references/adapters.md` before adapter probing

## Authority order

1. Explicit current user outcome and constraints.
2. Validated IdeaOS decision / pack, including source authority and supersession.
3. Live downstream owner contracts.
4. Current repository state and repo-local law.
5. This skill's **independently validated** Envelope, Graph, adapter evidence, and Receipt.
6. Older artifacts and historical examples.
7. Unknown: fail closed rather than guessing.

A supplied derived artifact does not outrank its parent merely because it says READY.

## Activation / reject

Activate after IdeaOS has established required outcomes, constraints, unresolved unknowns, and affected surfaces.

Reject:

- raw ideas that still require IdeaOS semantic development;
- generic coding requests;
- ceremonial re-planning of a current execution-ready pack;
- requests that treat local execution as implicit push, PR, merge, publication, or deployment authority.

## Non-goals

Never:

- redo IdeaOS product judgment;
- create a new repository when an existing owner or specialized factory already owns the capability;
- compile or mutate Program Execution internals to bypass its public front door;
- split one atomic multi-repo campaign merely to fit an executor limitation;
- regenerate a current higher-authority plan ceremonially;
- treat malformed or stale adapter evidence as executor incapability;
- create a fourth top-level remediation artifact beside Envelope, Graph, and Receipt;
- guess an owner, adapter capability, publication authority, or downstream terminal state.

## Core artifacts

Use three top-level execution artifacts only:

1. **Idea Execution Envelope**: normalized execution requirements.
2. **Execution Graph**: atomic units, owners/adapters, dependencies, blockers, and exact Envelope digest binding.
3. **Idea Execution Receipt**: thin join over the exact Envelope + Graph plus downstream owner states and reconciliation provenance.

Adapter Capability Snapshots are evidence artifacts, not a fourth control-plane layer.

## Workflow

### 1. Establish IdeaOS authority

Require a validated IdeaOS decision, pack, or equivalent execution authority.

Accepted decision vocabulary:

```text
GO
CONDITIONAL_GO
```

If semantic development is still required, stop with `IDEAOS_DECISION_REQUIRED`.

Preserve supersession. Never resurrect stale source material as current intent.

### 2. Compile the Idea Execution Envelope

Normalize once into `l9.idea-execution-envelope/v1`.

Requirements express capabilities and outcomes, never executor names.

Validate:

```bash
python3 scripts/validate_envelope.py IDEA_EXECUTION_ENVELOPE.yaml
```

Stop on failure.

### 3. Reconcile supplied execution artifacts before reuse

If the source includes a Graph, Receipt, adapter snapshot, plan, handoff, or other derived execution artifact, prove it is current before preserving it.

Run the deterministic pack preflight when applicable:

```bash
python3 scripts/preflight_execution_pack.py \
  --envelope IDEA_EXECUTION_ENVELOPE.yaml \
  --graph EXECUTION_GRAPH.yaml \
  --receipt IDEA_EXECUTION_RECEIPT.yaml \
  --adapter adapter-capabilities.yaml
```

Use these dispositions:

- `REUSABLE`
- `REPAIRABLE`
- `BLOCKED`

Regenerate from the earliest invalid derived layer. Do not rerun IdeaOS merely because a Graph or Receipt is stale.

Apply:

> Preserve the highest-authority **currently bound and independently validated** execution artifact.

### 4. Classify execution topology

Compile from the validated Envelope:

```bash
python3 scripts/route_execution.py IDEA_EXECUTION_ENVELOPE.yaml > EXECUTION_GRAPH.yaml
python3 scripts/validate_graph.py EXECUTION_GRAPH.yaml IDEA_EXECUTION_ENVELOPE.yaml
```

Topologies:

- `NEW_PRODUCT_REPOSITORY`
- `SPECIALIZED_FACTORY`
- `EXISTING_REPO_CHANGE`
- `EXISTING_SYSTEM_CAMPAIGN`

A structurally valid Graph with the wrong `source_envelope_digest` is `DERIVED_ARTIFACT_STALE`.

### 5. Resolve owners before executors

Examples:

- website artifact -> `Quantum-L9/Website-Bot`;
- generic unowned new product/system repository -> `l9-idea-foundry`;
- bounded existing-repository change -> current `l9-plan-simple` path when planning is needed;
- coordinated existing-system campaign -> Program Execution adapter.

A coding executor never becomes runtime/artifact owner merely by modifying a repository.

Unknown ownership -> `CAPABILITY_OWNER_UNKNOWN`.

### 6. Discover and bind the adapter contract

Treat downstream adapters as moving boundaries.

Before mutable handoff:

1. inspect the current public intake/front door;
2. capture exact repository revision/path evidence;
3. compile `l9.idea-execute.adapter-capabilities/v2`;
4. validate the snapshot;
5. determine whether requested topology is supported;
6. compile only current owner-native input;
7. validate owner-native input where supported;
8. invoke only the canonical public front door.

Validate adapter evidence:

```bash
python3 scripts/validate_adapter_snapshot.py adapter-capabilities.yaml
```

Evaluate a unit:

```bash
python3 scripts/check_adapter_capability.py \
  EXECUTION_GRAPH.yaml adapter-capabilities.yaml \
  --envelope IDEA_EXECUTION_ENVELOPE.yaml \
  --unit <unit-id>
```

Capability states:

- `COMPATIBLE`: valid current evidence proves support;
- `EXECUTOR_CAPABILITY_GAP`: valid current evidence proves non-support;
- `ADAPTER_CAPABILITY_UNKNOWN`: valid evidence does not resolve support.

Malformed or stale evidence instead produces `ADAPTER_SNAPSHOT_INVALID`, `ADAPTER_SNAPSHOT_STALE`, or `ADAPTER_CONTRACT_CONFLICT`.

Never degrade the requested topology merely to fit the tool.

### 7. Invoke only with bounded authority

Execution authority is unit-local. Push, PR publication, remote repo creation, merge, deployment, and protected actions remain separate unless explicitly authorized by the user and downstream contract.

Never widen one unit's authority because another unit has stronger permission.

### 8. Observe authoritative downstream state

Capture the downstream owner's canonical receipt/state and its input binding where available.

Do not recreate downstream evidence as a substitute for the owner's receipt.

### 9. Join the Idea Execution Receipt

Produce `l9.idea-execution-receipt/v1` with:

- exact Envelope digest;
- exact Graph digest;
- every Graph unit;
- owner/adapter/resulting state;
- canonical downstream receipt/state references;
- blockers;
- next legal transition;
- reconciliation provenance for reused, regenerated, and superseded artifacts.

Validate:

```bash
python3 scripts/validate_receipt.py \
  IDEA_EXECUTION_RECEIPT.yaml EXECUTION_GRAPH.yaml IDEA_EXECUTION_ENVELOPE.yaml
```

### 10. Resume from the earliest invalid layer

On rerun:

- reuse units only when governing inputs, dependency outputs, adapter source bindings, and downstream receipts remain valid;
- invalidate the earliest changed layer and its dependency cone;
- preserve unrelated siblings;
- never reuse publication/deployment authorization merely because local code evidence is reusable.

## Topology rules

### Specialized factory outranks generic birth

Use Foundry only for an unowned new **product/system repository**. A website routes directly to Website-Bot even if Website-Bot internally provisions a repository.

### Existing system campaign

Use `EXISTING_SYSTEM_CAMPAIGN` when multiple existing repositories participate in one causal program or share convergence/rollback/join requirements.

Do not decompose an atomic campaign solely because current admission cannot represent it.

### Bounded existing-repository change

Use `EXISTING_REPO_CHANGE` when one existing repository can satisfy the outcome without cross-repository convergence.

This is a first-class success path, not failed repository birth.

Reuse a valid existing plan first. Invoke planning only when current execution artifacts are insufficient.

## Adapter invariants

### Foundry

Use only for unowned new product/system repositories. Let Foundry own realization, traceability, freeze, and repo-template birth.

### Website-Bot

Compile rich authoring input and let Website-Bot own its internal normalization, pipeline, provisioning, publication, and deployment boundaries.

### Plan Simple

Conditional for bounded existing-repository work. Inspect its live contract and current handoff modes. Reuse valid planning evidence when sufficient.

### Program Execution

Always inspect the live front door. `references/program-execution-adapter.md` is a discovery baseline, not permanent law.

## Determinism and evidence

- Normalize IdeaOS authority once.
- Route from the Envelope, not repeatedly from raw prose.
- Keep stable requirement and unit IDs.
- Use explicit dependencies and failure states.
- Bind derived machine artifacts to parents by digest.
- Bind moving repository contracts by revision/path and optional content digest.
- Keep human-readable source refs alongside machine bindings.
- Never let structural validity substitute for lineage validity.

## Failure states

Use explicit states:

- `IDEAOS_DECISION_REQUIRED`
- `ENVELOPE_INVALID`
- `DERIVED_ARTIFACT_STALE`
- `CAPABILITY_OWNER_UNKNOWN`
- `EXECUTION_TOPOLOGY_UNSUPPORTED`
- `ADAPTER_CONTRACT_UNAVAILABLE`
- `ADAPTER_SNAPSHOT_INVALID`
- `ADAPTER_SNAPSHOT_STALE`
- `ADAPTER_CONTRACT_CONFLICT`
- `ADAPTER_CAPABILITY_UNKNOWN`
- `EXECUTOR_CAPABILITY_GAP`
- `OWNER_NATIVE_INPUT_INVALID`
- `DOWNSTREAM_EXECUTION_FAILED`
- `DOWNSTREAM_RECEIPT_INVALID`
- `PROTECTED_ACTION_REQUIRES_AUTHORITY`

A blocked route is valid when the idea is sound but current evidence or executor substrate is incomplete.

## Regression examples

Read `references/examples.md`. The canonical cases include:

- new standalone product -> Foundry;
- website-only -> Website-Bot;
- bounded existing repo -> Plan Simple path;
- multi-repo campaign -> Program Execution path;
- mixed product + website -> separate units with explicit dependencies;
- IgorBot voice/follow-up exercise -> existing owner, stale Graph rejected, malformed adapter evidence rejected, current Plan Simple evidence accepted.

## Validation

Run:

```bash
python3 scripts/self_test.py
```

The self-test must prove both positive routing and negative lineage/evidence behavior.

## Scripts

- `scripts/validate_envelope.py`: validate normalized execution authority.
- `scripts/route_execution.py`: deterministically compile the initial Graph.
- `scripts/validate_graph.py`: validate Graph structure and exact Envelope binding.
- `scripts/validate_adapter_snapshot.py`: validate revision-bound adapter evidence and compare source bindings.
- `scripts/check_adapter_capability.py`: evaluate topology support as compatible, proven gap, or Unknown.
- `scripts/validate_receipt.py`: validate Receipt against exact Envelope and Graph.
- `scripts/preflight_execution_pack.py`: classify supplied execution artifacts as reusable, repairable, or blocked.
- `scripts/self_test.py`: deterministic regression suite.

These scripts validate declared execution semantics. They do not replace semantic judgment for ambiguous IdeaOS meaning or downstream owner-specific input compilation.
