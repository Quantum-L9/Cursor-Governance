<!-- L9_META
skill_schema: 1
parent: l9-recursive-optimization
layer: reference
role: improvement_protocol
tags: [recursive, improvement, hardening, enforceability]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-06-06
sources:
  - Recursive Improvement.md
/L9_META -->

# Improvement Protocol

## Purpose

Materially improve an artifact group while preserving original intent, scope, behavior, interfaces, architecture, and required outputs. Different from alignment: the job is to make artifacts better, not only to check compliance.

## Source Scope

May be: single file, multiple files, folder, repo pack, spec pack, build plan, prompt chain, audit bundle, roadmap, execution guide, or mixed artifact group.

## Hard Rules

- Use provided artifact group as primary source of truth.
- Preserve original intent, scope, required outputs, and file/pack structure unless structure itself is the problem.
- Preserve architecture boundaries.
- Preserve L9 TransportPacket/Gate/SDK laws when applicable.
- Do NOT invent missing requirements.
- Do NOT add unrequested implementation.
- Do NOT generate new files unless source pack contract requires them.
- Do NOT collapse multi-file pack into single artifact.
- Do NOT change behavior silently.
- Do NOT create parallel architecture.
- Do NOT weaken constraints.
- Do NOT leave soft language where enforcement is needed.
- Label `Unknown` when source support is missing.

## Improvement Targets

Improve every file and section across: objective clarity, role definition, input/output contracts, execution sequence, validation gates, authority boundaries, failure handling, acceptance criteria, convergence logic, naming consistency, scope control, enforcement strength, reuse value, agent executability, pack coherence.

## Recursive Passes

| Pass | Action |
|------|--------|
| 1 extract | Artifact type, structure, purpose, user, inputs, outputs, constraints, implied contracts, dependencies, validation method, completion criteria |
| 2 classify | Tag each section: objective, context, rule, workflow, artifact contract, validation gate, acceptance criterion, failure mode, output requirement, source material, or unsupported/unclear |
| 3 audit | Ambiguity, duplication, weak phrasing, missing gates, missing failure behavior, hidden assumptions, drift risk, architecture leakage, unsupported claims, non-executable instructions, pack conflicts, broken cross-file routing |
| 4 strengthen | Convert vague language to explicit MUST / MUST NOT / SHOULD; preserve meaning; increase enforceability |
| 5 deduplicate | Collapse repeated rules; merge overlapping sections; preserve strongest formulation without deleting unique contract meaning |
| 6 normalize | Terminology, ordering, naming, output schemas, validation language, L9 references, file roles, cross-file references |
| 7 clarify and relocate | Clarify unclear sections; relocate to correct file/section when structure supports it; do not invent files |
| 8 enforce | Sharpen validation gates, failure conditions, acceptance criteria, cross-file consistency checks, convergence checks |
| 9 validate | Verify improved group preserves intent; improves completeness, clarity, enforceability, reuse, coherence, execution readiness |
| 10 converge | Re-run until changes stop materially improving; stop when additional edits add noise not leverage |

## Validation Gates (all MUST pass)

- artifact_group_type_identified
- file_or_pack_structure_preserved_or_intentionally_corrected
- source_intent_preserved
- no_unsupported_scope_added
- no_behavior_regression
- constraints_strengthened_not_weakened
- output_contracts_complete
- validation_gates_complete
- failure_modes_explicit
- cross_file_references_valid
- L9_boundaries_preserved_when_applicable
- duplicate_or_weak_sections_removed
- improved_artifact_group_executable_without_reinterpretation
- convergence_reached

## Output Requirements

| Must return | Must NOT return (default) |
|-------------|---------------------------|
| complete revised artifact group or pack | single improved artifact when pack is required |
| all modified file contents when file-based | partial patch when complete pack required |
| revised folder tree when pack-based | summary-only when user asked for full pack |
| convergence_block | — |

Format: same as source group unless user requests otherwise.
