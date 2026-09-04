# Foundry contracts

Use these as semantic contracts. YAML field order may vary; meanings may not.

## Contents

- [1. IdeaAuthorityMap](#1-ideaauthoritymap)
- [2. Beneficiary and reuse map](#2-beneficiary-and-reuse-map)
- [3. ImplementationBlueprint](#3-implementationblueprint)
- [4. TraceabilityMap](#4-traceabilitymap)
- [5. FoundryReceipt](#5-foundryreceipt)
- [6. FoundryIndex](#6-foundryindex)
- [7. FreezeReceipt](#7-freezereceipt)
- [8. Typed Foundry blockers](#8-typed-foundry-blockers)

## 1. IdeaAuthorityMap

```yaml
schema: l9.idea-foundry.authority-map/v1
sources:
  - ref: 00_CANON/CANONICAL_THESIS.md
    digest: sha256:...
    state: CANONICAL
    governs: [product_thesis]
claims:
  - id: product_thesis
    source_refs: [00_CANON/CANONICAL_THESIS.md]
    state: CANONICAL
    statement: "..."
conflicts: []
```

Allowed states:

`CANONICAL | LOCKED | ACCEPTED | PROPOSED | HYPOTHESIS | UNKNOWN | REJECTED | DEFERRED | SUPERSEDED`

Contradiction precedence: explicit current user instruction, then explicit pack supersession/change-control law, then source authority. Newer timestamps do not automatically outrank stronger authority.

Every selected-slice capability must resolve to cited claims. Do not make the raw pack a second live interpretation surface after the compiled intent is accepted.

## 2. Beneficiary and reuse map

Embed this inside the implementation blueprint.

```yaml
beneficiary:
  repository: example
  package: example
  template_class: non_constellation_python
  product_responsibilities: []
  external_authorities: []
reuse_map:
  - responsibility: semantic_memory
    verified_owner: Quantum-L9/example-owner
    disposition: CONSUME_UPSTREAM
    evidence_refs: [github:Quantum-L9/example-owner/.l9/architecture.yaml]
    integration_shape: dependency
  - responsibility: product_specific_state
    verified_owner: null
    disposition: OWN_LOCALLY
    evidence_refs: [owner-search:no-existing-owner]
    integration_shape: local_owner
```

Allowed dispositions:

- `CONSUME_UPSTREAM`: use the verified owner directly.
- `ADAPT_UPSTREAM`: keep upstream semantic ownership and add only a bounded product adapter.
- `HARVEST_THEN_DECIDE`: semantic fit is material and must be resolved through `l9-intelligence-harvest` before ownership is chosen.
- `OWN_LOCALLY`: responsibility is product-specific or no verified shared owner fits.
- `DEFER_OUTSIDE_SLICE`: do not solve in the selected compile slice.
- `BLOCKED_UNKNOWN`: ownership cannot yet be established safely.

Rules:

- Do not invent a verified owner.
- `CONSUME_UPSTREAM` and `ADAPT_UPSTREAM` require a named verified owner.
- Any non-deferred disposition requires evidence.
- `OWN_LOCALLY` is not the default. Search upstream first.
- A product adapter may translate a contract but may not become the new shared brain.

## 3. ImplementationBlueprint

This is the **pre-code single ingress**. Once accepted, Plan Simple and code realization consume this compiled intent rather than independently reinterpreting the raw pack. Raw sources remain available as cited evidence and are re-opened only when an explicit change or contradiction invalidates this layer.

```yaml
schema: l9.idea-foundry.implementation-blueprint/v1
identity:
  repository: example
  package: example
objective:
  product_thesis: "..."
  first_executable_outcome: "..."
compilation:
  ingress_role: PRE_CODE_SSOT
  source_inventory_digest: sha256:...
  authority_map_ref: docs/idea-origin/AUTHORITY_MAP.yaml
  raw_source_after_acceptance: EVIDENCE_ONLY
  change_policy: EARLIEST_INVALID_LAYER
beneficiary: {}
reuse_map: []
constellation_leverage:
  highest_leverage_move: "..."
  upstream_reuse: []
  duplicate_owners_avoided: []
  compounding_contracts: []
  future_actions_accelerated: []
  speculative_abstractions_rejected: []
invariants: []
anti_goals: []
architecture:
  style: modular_monolith
  stack: {}
  owners: []
  boundaries: []
  modules: []
  dependency_direction: []
contracts:
  persisted_models: []
  apis: []
  deterministic_engines: []
  model_mediated_surfaces: []
intelligence_harvest:
  status: NOT_APPLICABLE
  harvest_ref: null
  receipt_ref: null
  accepted_nugget_refs: []
planning:
  owner: l9-plan-simple
  plan_document_ref: docs/idea-origin/IMPLEMENTATION.plan.json
  plan_digest: sha256:...
  validation_status: PASSED
  plan_handoff: EMBEDDED
  mode_evidence_ref: skills/l9-plan-simple/SKILL.md
  compatibility_fallback: false
acceptance:
  path: []
  evidence_required: []
unknowns: []
deferred: []
validation_obligations: []
architecture_questions:
  direction: {verdict: SATISFIED, evidence_refs: []}
  constellation_alignment: {verdict: SATISFIED, evidence_refs: []}
  first_order: {verdict: SATISFIED, evidence_refs: []}
```

### Planning handoff negotiation

Prefer first-class Plan Simple embedded mode when current evidence proves it exists:

```yaml
plan_handoff: EMBEDDED
mode_evidence_ref: <current Plan Simple contract or emitted plan evidence>
compatibility_fallback: false
```

Until that mode is available, preserve the existing bounded compatibility path:

```yaml
plan_handoff: EMBEDDED_PRE_BIRTH
compatibility_fallback: true
fallback_reason: "current l9-plan-simple lacks first-class embedded mode"
```

Never infer embedded mode merely because execution or publication tools are unavailable. Missing capability is a blocker, not mode selection.

### Constellation leverage contract

`constellation_leverage` owns cross-repository leverage only. It must not duplicate Plan Simple's implementation-level leverage ranking.

- `highest_leverage_move`: the one upstream/ownership/boundary move that most reduces repeated future work or risk.
- `upstream_reuse`: verified capabilities consumed rather than rebuilt.
- `duplicate_owners_avoided`: shared responsibilities deliberately not cloned into the newborn.
- `compounding_contracts`: new or strengthened contracts justified by multiple verified consumers or a recurring operation.
- `future_actions_accelerated`: concrete later actions made cheaper or safer by the compile.
- `speculative_abstractions_rejected`: tempting abstractions intentionally not created because reuse is unproven.

Do not count additional files, generic interfaces, or abstraction layers as leverage by themselves.

### Architecture default

Prefer a modular monolith unless evidence forces distributed ownership, independent scaling, hard isolation, or separate deployment lifecycle. Conceptual services are responsibilities first.

## 4. TraceabilityMap

Traceability is the durable bridge from idea authority to code and tests. It exists so future agents can change the newborn without reverse-engineering why each surface exists.

```yaml
schema: l9.idea-foundry.traceability/v1
capabilities:
  - id: CAP-001
    status: IMPLEMENTED
    requirement_refs: [claim:product_thesis]
    architecture_refs: [blueprint:architecture.modules.core]
    harvest_refs: []
    plan_todo_refs: [TODO-001]
    implementation_paths: [src/example/core.py]
    evidence_refs: [tests/test_core.py::test_outcome]
    unknown_ids: []
implementation_decisions:
  - id: DEC-001
    statement: "..."
    source_truth: false
    rationale: "reversible implementation default"
    affected_paths: [src/example/core.py]
```

Status values:

`IMPLEMENTED | PARTIAL | DEFERRED | BLOCKED`

Rules:

- Every canonical requirement in the selected slice must appear.
- Every nontrivial implementation surface must resolve to a requirement or explicit implementation decision.
- `IMPLEMENTED` requires source requirement refs, plan todo refs, implementation paths, and executable evidence refs.
- Do not duplicate the same provenance into a second traceability artifact.

## 5. FoundryReceipt

`FOUNDRY_RECEIPT.yaml` records run state and composition. It is human-readable operational provenance; `FOUNDRY_INDEX.json` is the deterministic resume/index surface.

```yaml
schema: l9.idea-foundry.receipt/v1
run:
  status: CODE_REALIZED_LOCAL
source:
  input_ref: "..."
  inventory_digest: sha256:...
  source_revision: null
composition:
  intelligence_harvest:
    status: NOT_APPLICABLE
    harvest_ref: null
    receipt_ref: null
  gar:
    status: NOT_USED
    decision_ref: null
  planning:
    owner: l9-plan-simple
    plan_document_ref: "..."
    plan_digest: sha256:...
    validation_status: PASSED
    plan_handoff: EMBEDDED
    compatibility_fallback: false
payload:
  path: "..."
  freeze_binding: EXTERNAL_RECEIPT
  resume_index_ref: docs/idea-origin/FOUNDRY_INDEX.json
validation:
  commands: []
  results: []
birth:
  template_repo: Quantum-L9/l9-repo-template
  payload_contract: null
  local_birth_state: null
  remote_birth_state: null
  repository_url: null
deployment:
  performed: false
unknowns: []
deferred: []
```

Allowed run statuses:

`INTAKE | MODELED | PLANNED | CODE_REALIZED_LOCAL | BIRTH_READY | LOCAL_BIRTH_PASS | PROVISIONAL_REPOSITORY | QUARANTINED | BLOCKED`

There is no `DEPLOYED` state.

## 6. FoundryIndex

Generate `docs/idea-origin/FOUNDRY_INDEX.json` with `scripts/emit_foundry_index.py` after code realization and before payload freeze.

This is the **post-realization single ingress** for downstream agents. It indexes current origin artifacts and their digests so a future agent can hydrate only what changed instead of rediscovering the entire idea pack.

```json
{
  "schema": "l9.idea-foundry.index/v1",
  "source": {
    "input_ref": "...",
    "inventory_digest": "sha256:...",
    "source_revision": null
  },
  "compiled_intent": {
    "pre_code_ingress": "docs/idea-origin/IMPLEMENTATION_BLUEPRINT.yaml",
    "raw_source_policy": "EVIDENCE_ONLY_AFTER_ACCEPTANCE"
  },
  "composition": {
    "planning": {
      "owner": "l9-plan-simple",
      "plan_digest": "sha256:...",
      "plan_handoff": "EMBEDDED"
    }
  },
  "artifacts": {},
  "lineage": {
    "inventory_digest": "sha256:...",
    "authority_digest": "sha256:...",
    "blueprint_digest": "sha256:...",
    "traceability_digest": "sha256:...",
    "plan_digest": "sha256:..."
  },
  "resume": {
    "entrypoint": "docs/idea-origin/FOUNDRY_INDEX.json",
    "repair_policy": "EARLIEST_INVALID_LAYER",
    "after_remote_birth": "ORIGIN_EVIDENCE_ONLY_REPO_GROUND_TRUTH_WINS"
  },
  "deployment": {"performed": false}
}
```

The index is generated output. Do not hand-edit it. Regenerate it when any indexed artifact changes.

After remote birth, it remains useful provenance, not perpetual governance. Current repository ground truth, current repo law, and explicit current operator intent outrank stale origin artifacts.

## 7. FreezeReceipt

Emit this **outside** the staging repository after the payload, including `FOUNDRY_INDEX.json`, is committed and clean. It binds the immutable repository state without requiring a commit to contain its own hash.

```json
{
  "schema": "l9.idea-foundry.freeze-receipt/v1",
  "git_revision": "<40hex>",
  "tracked_file_count": 0,
  "tracked_tree_digest": "sha256:...",
  "inventory_digest": "sha256:...",
  "plan_ref": "...",
  "plan_digest": "sha256:...",
  "foundry_index_ref": "docs/idea-origin/FOUNDRY_INDEX.json",
  "foundry_index_digest": "sha256:..."
}
```

The birth-ready validator must recompute HEAD, tracked-tree digest, plan binding, source inventory binding, and index digest and require exact equality.

## 8. Typed Foundry blockers

Use stable blocker labels in receipts and final output:

- `SOURCE_AUTHORITY_BLOCKED`
- `BENEFICIARY_OWNERSHIP_BLOCKED`
- `HARVEST_CAPABILITY_BLOCKED`
- `ARCHITECTURE_BLOCKED`
- `PLANNING_CAPABILITY_BLOCKED`
- `PLAN_VALIDATION_FAILED`
- `CODE_REALIZATION_FAILED`
- `VALIDATION_FAILED`
- `TEMPLATE_MISMATCH`
- `BIRTH_INTEGRATION_FAILED`
- `REMOTE_BIRTH_BLOCKED`

Do not turn a blocker into `NOT_APPLICABLE` merely because a capability is missing.
