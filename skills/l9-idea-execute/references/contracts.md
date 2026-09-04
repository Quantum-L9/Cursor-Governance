<!-- L9_META
l9_schema: 1
parent: l9-idea-execute
layer: reference
role: contracts
tags: [ideaos, envelope, graph, receipt]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-09-02
/L9_META -->

# Contracts

## Table of contents

1. Idea Execution Envelope
2. Execution Graph
3. Adapter Capability Snapshot
4. Owner-native handoff
5. Idea Execution Receipt
6. Digests and traceability

## 1. Idea Execution Envelope

Use YAML or JSON with this semantic shape:

```yaml
schema: l9.idea-execution-envelope/v1
idea:
  id: cognitive-convergence
  title: L9 PR Cognitive Convergence
  decision_status: GO
  source_refs:
    - 06_ROUTING_DECISION.md
requirements:
  - id: ER-001
    capability: repository_change
    target_state: modify
    required: true
    target_repo: Quantum-L9/PR_Repair
    dependencies: []
    authority_refs: []
    unknown_ids: []
execution_characteristics:
  cross_repository: true
  code_required: true
  runtime_validation_required: true
  protected_actions: []
  repositories:
    - Quantum-L9/PR_Repair
    - Quantum-L9/LLM-Router
    - Quantum-L9/l9-cognitive-runtime
existing_execution:
  plan_refs: []
  contract_refs: []
  acceptance_refs: []
  rollback_refs: []
  handoff_refs: []
```

Rules:

- `decision_status` must be `GO` or `CONDITIONAL` to route execution.
- Every requirement has a stable unique ID.
- `dependencies` refer to requirement IDs.
- `capability` expresses the needed outcome, not a skill/tool name.
- `target_repo` is required for `repository_change`.
- `website` should not also request a generic repository for the factory's internal site repo.
- Unknowns that prevent truthful compilation remain explicit.

## 2. Execution Graph

`route_execution.py` emits:

```yaml
schema: l9.idea-execution-graph/v1
source_envelope_digest: sha256:...
status: READY
units:
  - id: unit-campaign
    topology: EXISTING_SYSTEM_CAMPAIGN
    owner: Cursor-Governance/Program-Execution
    adapter: program-execution
    requirement_ids: [ER-001, ER-002, ER-003]
    target_repos:
      - Quantum-L9/PR_Repair
      - Quantum-L9/LLM-Router
      - Quantum-L9/l9-cognitive-runtime
    depends_on_units: []
    admission_status: UNCHECKED
blockers: []
```

Graph rules:

- unit IDs are unique;
- each requirement appears in exactly one unit;
- dependency edges must be acyclic;
- specialized-factory units never route through Foundry;
- a campaign unit may contain multiple runtime owners but only one execution adapter;
- `READY` means routable to adapter probing, not permission to mutate.

## 3. Adapter Capability Snapshot

Capture live discovery in a small snapshot before mutation:

```yaml
schema: l9.idea-execute.adapter-capabilities/v1
adapter: program-execution
observed_at: 2026-09-02T00:00:00Z
source_refs:
  - skills/l9-pe-campaign-activate/SKILL.md
  - skills/l9-pe-campaign-activate/references/source-contract.md
front_door:
  kind: command
  value: make campaign INTENT=<path>
accepted_inputs:
  - brief
  - activate_yaml
topologies:
  single_target: true
  multi_target: false
authority:
  local_commits: true
  push: false
  open_pr: false
  merge: false
```

The snapshot is evidence about a moving owner contract. It is not a permanent registry entry.

## 4. Owner-native handoff

The owner-native input must be compiled from the execution unit plus authoritative source facts.

Examples:

- Website-Bot: rich `domain_spec.source.yaml`;
- Program Execution: whatever current live `make campaign INTENT=` accepts;
- Foundry: its current idea-to-repository intake;
- Plan Simple: its current planning input.

Never invent a universal handoff schema and force downstream owners to consume it.

## 5. Idea Execution Receipt

Use a thin join record:

```yaml
schema: l9.idea-execution-receipt/v1
idea_id: cognitive-convergence
envelope_digest: sha256:...
graph_digest: sha256:...
status: BLOCKED
units:
  - unit_id: unit-campaign
    owner: Cursor-Governance/Program-Execution
    adapter: program-execution
    requested_terminal_state: verified_local_commits
    resulting_state: EXECUTOR_CAPABILITY_GAP
    native_input_ref: null
    downstream_receipt_ref: null
    evidence_refs:
      - pe-capabilities.yaml
blockers:
  - code: EXECUTOR_CAPABILITY_GAP
    unit_id: unit-campaign
    detail: current PE admission contract cannot represent a multi-target campaign
next_legal_transition: re-probe Program Execution after its admission contract changes
```

Do not duplicate downstream evidence inside this receipt.

## 6. Digests and traceability

Prefer SHA-256 over machine artifacts when available. Bind:

- envelope -> graph;
- graph unit -> native handoff;
- native handoff -> downstream receipt/state where supported.

Keep human source refs alongside digests so an operator can understand why a route exists.
