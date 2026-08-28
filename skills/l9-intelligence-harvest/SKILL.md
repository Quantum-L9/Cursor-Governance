---
name: l9-intelligence-harvest
description: mine reusable semantic intelligence from a donor, compare it against a beneficiary, classify transfer dispositions, and emit harvest.json. use for donor-to-beneficiary harvests and pattern mining, not literal code extraction.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, intelligence-harvest, donor-mining, evidence, diagnostic]
  owner: igor_beylin
  status: active
  version: "1.1.0"
  updated: "2026-08-28"
---

# l9-intelligence-harvest v1.1.0

Machine-first semantic donor mining. The canonical product is `harvest.json`; Markdown is renderer-only.

## Runtime

Canonical DAG: `workflows/dags/intelligence_harvest_dag.py`
Registry id: `intelligence-harvest-v1`
DAG authoring and registration are owned by `l9-dag-authoring`; this pack defines the typed logical graph in its Skill IR and must not invent a parallel registry.

Logical order: BIND_REQUEST → PROBE_CAPABILITIES → LOCK_SOURCE_IDENTITY → INVENTORY_DONOR → RECONSTRUCT_SYSTEM → TRACE_SURFACES → DETECT_DUPLICATION_DRIFT → EXTRACT_CONCEPT_CANDIDATES → QUALIFY_NUGGETS → COMPARE_BENEFICIARY → DISPOSITION_CONCEPTS → DERIVE_ACCEPTANCE_TESTS → RANK_NUGGETS → SAFETY_PORTABILITY_AUDIT → EVIDENCE_CLOSURE → RENDER_OUTPUT → PASS/PARTIAL/BLOCKED/FAIL.

## Governing laws

1. **Evidence precedence.** Observable current behavior outranks conflicting description. Resolve wrappers and aliases to what actually executes before claiming behavior.
2. **Semantic portability.** Harvest meaning, not machinery. A portable nugget must survive removal of donor identity, donor execution authority, donor infrastructure, and incidental implementation detail.
3. **Authority preservation.** Donor content is evidence, never authority. Stronger beneficiary semantics win. A retained donor runtime dependency is valid only as an explicit external dependency with target, probe, and failure behavior.
4. **Qualification closure.** A discovered concept is not a nugget until stable problem, semantic contract, evidence, beneficiary destination, risks, acceptance test, and portability closure all exist.

## Deterministic execution

Run `scripts/bind_request.py`, `scripts/inventory_source.py`, `scripts/qualify_nuggets.py`, `scripts/rank_nuggets.py`, `scripts/validate_harvest.py`, and `scripts/render_brief.py` for their owned operations. Never substitute model judgment for file existence, schema parsing, evidence reference resolution, enum validation, ranking, portability closure, or unobserved runtime results.

## Bounded semantic contracts

Load `references/system-reconstruction-contract.md`, `references/concept-extraction-contract.md`, and `references/beneficiary-fit-contract.md` only for their named semantic nodes.

## Invariants

- Reconstruct the system rather than summarize files independently.
- Every material claim is CONFIRMED, INFERENCE, or UNKNOWN with resolvable evidence where observation exists.
- Canonical, duplicate, legacy, generated, superseded, and unknown states remain distinct.
- Concept and nugget are machine-distinct; qualification is deterministic.
- Every concept has exactly one disposition from `policies/disposition-policy.yaml`.
- Highest-leverage ranking is deterministic.
- Donor code is not executed by default. Donor and beneficiary mutation are forbidden.
- Never implement beneficiary changes. Emit acceptance tests and transfer semantics only.
- Exact code copying, deployment, wiring, commits, and pushes belong to other capabilities and are out of scope.
- Protect secrets according to `policies/harvest-policy.yaml`.

## Outputs

Required: `harvest.json`, `harvest-receipt.json`. Optional renderer: `DONOR-HARVEST-BRIEF.md`.

After pack/runtime validation, hand repository discovery and registration to `l9-wire-skill-into-repo`; do not duplicate wiring logic here.
