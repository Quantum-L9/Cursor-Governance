<!-- L9_META
l9_schema: 1
parent: l9-idea-execute
layer: reference
role: artifact-reconciliation
tags: [ideaos, execution, lineage, reconciliation, digests]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-09-12
/L9_META -->

# Artifact reconciliation

## Purpose

Derived execution artifacts are reusable only when their parent bindings independently prove that they are current. Structural validity is necessary but insufficient.

## Lineage

```text
validated IdeaOS authority
  -> Idea Execution Envelope
  -> Execution Graph
  -> unit-bound Adapter Capability Snapshot
  -> freshly discovered current adapter evidence
  -> owner-native handoff
  -> downstream owner receipt/state
  -> Idea Execution Receipt
```

Every derived layer must either bind to its governing parent/current authority by digest or revision evidence, or remain explicitly unverified.

## Preflight dispositions

Use exactly these pack-level dispositions:

- `REUSABLE`: every supplied artifact needed for the next transition is current and validated.
- `REPAIRABLE`: the source authority is valid, but one or more derived layers must be regenerated or rediscovered.
- `BLOCKED`: the source envelope itself is invalid or a higher-authority conflict prevents truthful repair.

Artifact-level dispositions:

- `REUSABLE`
- `STALE_REGENERATE`
- `INVALID`
- `UNRESOLVED`

A supplied adapter snapshot is `UNRESOLVED` until fresh current evidence for the same Graph unit is available. Structural validation of the snapshot alone is never enough to mark it reusable.

## Earliest-invalid-layer law

When a derived artifact is stale, regenerate or rediscover from the earliest invalid layer and invalidate only its dependency cone.

Examples:

```text
Envelope current + Graph stale
  -> regenerate Graph
  -> invalidate Receipt derived from that Graph
  -> keep unrelated source evidence
```

```text
Graph current + supplied Adapter snapshot stale
  -> rediscover current Adapter snapshot
  -> reconcile supplied evidence against current source bindings
  -> do not regenerate Envelope or Graph
```

```text
Graph current + Adapter snapshot bound to another unit
  -> ADAPTER_CONTRACT_CONFLICT
  -> do not reuse the unrelated evidence
```

Do not re-run IdeaOS merely because a derived execution artifact is stale.

## Canonical reason codes

Use these reason codes where applicable:

- `DERIVED_ARTIFACT_STALE`
- `PARENT_DIGEST_MISMATCH`
- `SOURCE_REVISION_CHANGED`
- `GRAPH_REQUIREMENT_COVERAGE_MISMATCH`
- `ADAPTER_SNAPSHOT_INVALID`
- `ADAPTER_SNAPSHOT_STALE`
- `ADAPTER_CONTRACT_CONFLICT`
- `ADAPTER_CAPABILITY_UNKNOWN`

Reserve `EXECUTOR_CAPABILITY_GAP` for a validated freshly discovered adapter snapshot that positively proves the requested topology is unsupported.

## Reconciliation receipt

Do not create a fourth top-level artifact layer. Record repair provenance inside the thin Idea Execution Receipt:

```yaml
reconciliation:
  reused:
    - ref: IDEA_EXECUTION_ENVELOPE.yaml
      reason: parent authority unchanged
  regenerated:
    - ref: EXECUTION_GRAPH.yaml
      reason: PARENT_DIGEST_MISMATCH
      replacement_ref: run/EXECUTION_GRAPH.yaml
  superseded:
    - ref: supplied/EXECUTION_GRAPH.yaml
      reason: DERIVED_ARTIFACT_STALE
      replacement_ref: run/EXECUTION_GRAPH.yaml
```

A superseded artifact remains evidence of history, never current execution authority.
