<!-- L9_META
l9_schema: 1
parent: l9-idea-execute
layer: reference
role: contracts
tags: [ideaos, envelope, graph, adapter, receipt, lineage]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-09-12
/L9_META -->

# Contracts

## Table of contents

1. Idea Execution Envelope
2. Execution Graph
3. Adapter Capability Snapshot
4. Owner-native handoff
5. Idea Execution Receipt
6. Binding and reconciliation law

## 1. Idea Execution Envelope

Use YAML or JSON with this semantic shape:

```yaml
schema: l9.idea-execution-envelope/v1
idea:
  id: example
  title: Example
  decision_status: GO
  source_refs: [06_ROUTING_DECISION.md]
requirements:
  - id: ER-001
    capability: repository_change
    target_state: modify
    required: true
    target_repo: Quantum-L9/example
    dependencies: []
    authority_refs: []
    unknown_ids: []
execution_characteristics:
  cross_repository: false
  code_required: true
  runtime_validation_required: true
  protected_actions: []
  repositories: [Quantum-L9/example]
existing_execution:
  plan_refs: []
  contract_refs: []
  acceptance_refs: []
  rollback_refs: []
  handoff_refs: []
```

Rules:

- `decision_status` is `GO` or `CONDITIONAL_GO`.
- Every requirement has one stable unique ID.
- Requirements declare capabilities/outcomes, never executor names.
- `target_repo` is required for `repository_change`.
- `cross_repository: true` requires at least two distinct repository-change targets.
- Unknowns that prevent truthful compilation remain explicit.

## 2. Execution Graph

`route_execution.py` emits `l9.idea-execution-graph/v1` and binds it to the exact semantic Envelope with `source_envelope_digest`.

Operational validation requires both artifacts:

```bash
python3 scripts/validate_graph.py EXECUTION_GRAPH.yaml IDEA_EXECUTION_ENVELOPE.yaml
```

Graph rules:

- unit IDs are unique;
- every Envelope requirement is represented exactly once, either by one execution unit or one requirement-scoped blocker;
- a requirement cannot appear in both a unit and a blocker;
- dependency edges are acyclic;
- specialized factories never route through Foundry;
- bounded existing-repo units target exactly one repository;
- campaign units target at least two repositories;
- `READY` means routable to adapter discovery, not permission to mutate;
- a graph whose `source_envelope_digest` no longer matches its Envelope is `DERIVED_ARTIFACT_STALE` even when structurally valid;
- missing, extra, or duplicated requirement coverage is `GRAPH_REQUIREMENT_COVERAGE_MISMATCH` or a structural validation failure.

## 3. Adapter Capability Snapshot

Use `l9.idea-execute.adapter-capabilities/v2` for live adapter evidence. Each snapshot is scoped to one exact Graph unit:

```yaml
schema: l9.idea-execute.adapter-capabilities/v2
unit_id: unit-existing-repo-change
adapter: l9-plan-simple
observed_at: 2026-09-12T00:00:00Z
source_refs:
  - skills/l9-plan-simple/SKILL.md
source_bindings:
  - repo: Quantum-L9/Cursor-Governance
    revision: <commit-sha>
    path: skills/l9-plan-simple/SKILL.md
    digest: sha256:<optional-content-digest>
front_door:
  kind: skill
  value: l9-plan-simple
accepted_inputs: [planning_intent]
topologies:
  single_target: true
  multi_target: null
authority:
  local_changes: true
  push: false
  merge: false
```

`true` means proven support, `false` means proven non-support, and `null` means Unknown.

A snapshot is evidence about a moving owner contract. It must bind to the Graph unit it evaluates and to exact repository source revisions/paths. Structural validity alone never proves freshness.

Validate shape:

```bash
python3 scripts/validate_adapter_snapshot.py current-adapter-capabilities.yaml
```

When a supplied/reused snapshot exists, compare it with freshly discovered current evidence:

```bash
python3 scripts/validate_adapter_snapshot.py \
  supplied-adapter-capabilities.yaml \
  --current current-adapter-capabilities.yaml
```

Different source bindings produce `ADAPTER_SNAPSHOT_STALE`. A different adapter/unit identity or contradictory contract fields at the same source bindings produce `ADAPTER_CONTRACT_CONFLICT`.

Capability judgment must use the freshly discovered current snapshot. A supplied snapshot may be reconciled in the same call:

```bash
python3 scripts/check_adapter_capability.py \
  EXECUTION_GRAPH.yaml current-adapter-capabilities.yaml \
  --supplied supplied-adapter-capabilities.yaml \
  --envelope IDEA_EXECUTION_ENVELOPE.yaml \
  --unit unit-existing-repo-change
```

Only validated current evidence may produce `EXECUTOR_CAPABILITY_GAP`.

## 4. Owner-native handoff

Compile the owner-native input from the execution unit plus authoritative source facts. Never invent a universal execution payload and force downstream owners to consume it.

Examples:

- Website-Bot: rich `domain_spec.source.yaml`;
- Program Execution: current public campaign intake;
- Foundry: current idea-to-repository intake;
- Plan Simple: current planning input/mode.

## 5. Idea Execution Receipt

Use a thin `l9.idea-execution-receipt/v1` join record:

```yaml
schema: l9.idea-execution-receipt/v1
idea_id: example
envelope_digest: sha256:...
graph_digest: sha256:...
status: BLOCKED
units:
  - unit_id: unit-existing-repo-change
    owner: l9-plan-simple
    adapter: l9-plan-simple
    requested_terminal_state: owner_native_handoff
    resulting_state: ADAPTER_CAPABILITY_UNKNOWN
    evidence_refs: [plan-simple-capabilities.yaml]
blockers: []
next_legal_transition: refresh adapter evidence
reconciliation:
  reused: []
  regenerated: []
  superseded: []
```

Validate the whole lineage:

```bash
python3 scripts/validate_receipt.py \
  IDEA_EXECUTION_RECEIPT.yaml EXECUTION_GRAPH.yaml IDEA_EXECUTION_ENVELOPE.yaml
```

Receipt units must exactly match Graph units by `unit_id`, `owner`, and `adapter`. The Receipt must also bind to the exact Envelope and Graph digests.

## 6. Binding and reconciliation law

Prefer SHA-256 semantic digests for machine artifacts and revision/path bindings for moving repository contracts.

Required chain:

```text
Envelope -> Graph -> owner-native handoff -> downstream receipt/state
             \
              -> unit-bound Adapter Capability Snapshot -> current source bindings
Graph + Envelope -> Idea Execution Receipt
```

Before reusing supplied derived artifacts, reconcile them against current evidence:

```bash
python3 scripts/preflight_execution_pack.py \
  --envelope IDEA_EXECUTION_ENVELOPE.yaml \
  --graph EXECUTION_GRAPH.yaml \
  --receipt IDEA_EXECUTION_RECEIPT.yaml \
  --adapter supplied-adapter-capabilities.yaml \
  --current-adapter current-adapter-capabilities.yaml
```

A supplied adapter snapshot without fresh current evidence is `UNRESOLVED`, not reusable. The pack result is `REUSABLE`, `REPAIRABLE`, or `BLOCKED`. See `artifact-reconciliation.md` for earliest-invalid-layer behavior and provenance rules.
