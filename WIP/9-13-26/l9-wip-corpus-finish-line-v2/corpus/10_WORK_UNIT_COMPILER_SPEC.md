# WorkUnitCompiler Specification

## Purpose
Convert graph-backed evidence into bounded work units. Prioritize work, not files.

## Construction rules
A WorkUnit must have one objective, a coherent completion condition, explicit supporting artifacts/evidence, and a bounded dependency neighborhood. Split a candidate when different parts can complete independently or have materially different owners/risks.

## Sources
- explicit TODO/tasks/milestones
- project/cluster candidates
- roadmaps/plans/specs
- dependency/blocker graph
- readiness evidence
- capability relationships
- current objective

## Required fields
identity, objective, state, artifact_ids, evidence_refs, prerequisites, dependents, blockers, capabilities_unlocked, readiness dimensions, effort/risk estimates with confidence, leverage dimensions, unknowns, completion_evidence.

## Prohibitions
- no priority from filename/date alone
- no percent-complete fabricated from TODO counts
- no merge of semantically similar work without evidence
- no execution instructions that belong to Program Execution

## Deep implementation
Reference implementation: `implementation/phase5_6/work_unit_compiler.py`. Build contract: `contracts/claude_code/PR-02-PHASE6A-WORK-UNIT-COMPILER.contract.yaml`.
