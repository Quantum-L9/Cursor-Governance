<!-- L9_META
skill_schema: 1
parent: l9-recursive-optimization
layer: reference
role: alignment_protocol
tags: [recursive, alignment, audit, l9, violations]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-06-06
sources:
  - Recursive Alignment.md
/L9_META -->

# Alignment Protocol

## Purpose

Read-only recursive audit of an artifact group against the active architecture contract. Produces a convergence-ready alignment report and correction roadmap. Does not implement fixes unless explicitly instructed.

## Source Authority (highest first)

1. L9 Master Kernel v3.0 (when L9 artifact)
2. TransportPacket-only coding stack (when inter-node wire format applies)
3. Node build protocol (logic/spec packs)
4. Microservice build pipeline (service build phases)
5. Workspace invariants (`AGENTS.md`, `INVARIANTS.md`, module rules) in project repos

## Non-Negotiables (L9 — when applicable)

Load [l9-context-rules.md](l9-context-rules.md). Violations are critical unless evidence shows otherwise.

## Recursive Passes

### Pass 1 — Context lock

Inspect: artifact type, target repo/pack, declared purpose, node role, ownership boundary, expected outputs.

Output: normalized context record, unknowns, scope boundary.

### Pass 2 — Transport alignment (L9)

Verify: TransportPacket-only; no PacketEnvelope; no raw dict transport fallback; no in-place packet mutation; `derive_or_with_hop` semantics; trace_id and lineage preserved.

Skip when artifact has no transport layer.

### Pass 3 — Gate routing alignment (L9)

Verify: Gate-only egress; no peer URLs; no direct node dispatch; no private node registry; actions express intent only; Gate resolves destination.

Skip when artifact has no routing layer.

### Pass 4 — Authority boundary alignment

Verify: Gate owns routing/admission/resilience only; orchestrator owns workflow only when explicitly an orchestrator; runtime node owns execution only; engine does not implement chassis responsibilities; no infra leakage.

### Pass 5 — File structure alignment

Verify: allowed file structure; no forbidden top-level dirs; handlers bridge location correct; spec files correctly placed; no generated infra files unless in scope; L9_META present on tracked files.

### Pass 6 — Schema and field alignment

Verify: snake_case only; YAML keys match Python fields; no aliases or camelCase; canonical field names; domain specs through typed models; no duplicated shared contract types.

### Pass 7 — Security and observability alignment

Verify: no eval/exec/compile; yaml.safe_load only; no print; no forbidden log fields; PII not logged; audit append-only; replay immutable; bounded caches.

### Pass 8 — Testing and validation alignment

Verify: behavior tests not grep theater; packet invariants tested when applicable; Gate routing boundaries tested; no PacketEnvelope scan passes; direct node call scan exists; no stub scanner passes; CI gates match claimed contracts.

### Pass 9 — Leverage and simplicity

Evaluate: overbuilt parts, underbuilt parts, duplicate logic, unnecessary abstractions, missing primitive boundaries, simplest correction with highest functional value.

### Pass 10 — Convergence

Reconcile: all violations, unknowns, correction priorities, alignment score, minimum safe next action.

## Violation Format

Every violation MUST include:

| Field | Values |
|-------|--------|
| id | stable identifier |
| severity | critical \| high \| medium \| low |
| rule_broken | contract clause |
| evidence | file:line or quoted excerpt |
| impact | what breaks if unfixed |
| correction | smallest safe fix |
| owner_layer | gate \| node \| engine \| pack \| infra \| unknown |
| blocks_release | true \| false |

## Correction Roadmap Rules

1. Order by dependency unlock first.
2. Fix transport and routing before cosmetics.
3. Fix authority boundaries before feature expansion.
4. Fix stubs before packaging.
5. Fix tests before ship verdict.
6. No implementation unless explicitly requested.

## Alignment Report Sections (required)

1. alignment_summary
2. source_authority_used
3. critical_violations
4. high_violations
5. medium_violations
6. unknowns
7. boundary_map
8. transport_packet_compliance (or N/A)
9. gate_routing_compliance (or N/A)
10. authority_boundary_compliance
11. file_structure_compliance
12. schema_field_compliance
13. security_observability_compliance
14. testing_validation_compliance
15. overbuilt_vs_underbuilt
16. correction_roadmap
17. minimum_safe_next_action
18. convergence_block
