<!-- L9_META
l9_schema: 1
parent: l9-idea-execute
layer: reference
role: contracts
tags: [ideaos, envelope, graph, adapter, receipt, lineage]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-09-11
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
- each requirement appears in exactly one unit;
- dependency edges are acyclic;
- specialized factories never route through Foundry;
- bounded existing-repo units target exactly one repository;
- campaign units target at least two repositories;
- `READY` means routable to adapter discovery, not permission to mutate;
- a graph whose `source_envelope_digest` no longer matches its Envelope is `DERIVED_ARTIFACT_STALE` even when structurally valid.

## 3. Adapter Capability Snapshot

Use `l9.idea-execute.adapter-capabilities/v2` for live adapter evidence:

```yaml
schema: l9.idea-execute.adapter-capabilities/v2
adapter: l9-plan-simple
observed_at: 2026-09-11T00:00:00Z
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

The snapshot is evidence about a moving owner contract. Source revision bindings are mandatory. Validate it before capability judgment:

```bash
python3 scripts/validate_adapter_snapshot.py adapter-capabilities.yaml
```

When a fresh discovery snapshot exists, compare bindings:

```bash
python3 scripts/validate_adapter_snapshot.py old.yaml --current current.yaml
```

Different bindings produce `ADAPTER_SNAPSHOT_STALE`; conflicting adapter identity produces `ADAPTER_CONTRACT_CONFLICT`.

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

Receipt units must exactly match graph units. The receipt must bind to the exact Envelope and Graph digests.

## 6. Binding and reconciliation law

Prefer SHA-256 semantic digests for machine artifacts and revision/path bindings for moving repository contracts.

Required chain:

```text
Envelope -> Graph -> owner-native handoff -> downstream receipt/state
             \
              -> Adapter Capability Snapshot source revisions
Graph + Envelope -> Idea Execution Receipt
```

Before reusing supplied derived artifacts, run:

```bash
python3 scripts/preflight_execution_pack.py \
  --envelope IDEA_EXECUTION_ENVELOPE.yaml \
  --graph EXECUTION_GRAPH.yaml \
  --receipt IDEA_EXECUTION_RECEIPT.yaml \
  --adapter adapter-capabilities.yaml
```

The pack result is `REUSABLE`, `REPAIRABLE`, or `BLOCKED`. See `artifact-reconciliation.md` for earliest-invalid-layer behavior and provenance rules.
