# Task-Scoped Retrieval / Context Compilation Playbook

## Objective
Given an objective, compile the minimum sufficient authoritative context required to reason or execute safely.

## Canonical output
WorkContextPacket / CompiledTaskContext projection containing:
- objective
- task_scope
- focal_entities
- authoritative_artifacts
- supporting_artifacts
- upstream_dependencies
- downstream_dependencies
- blockers
- supersession current/superseded/ambiguous
- contradictions
- unresolved_unknowns
- readiness_evidence
- candidate_relations
- evidence_refs
- exclusions with reasons
- retrieval provenance

## Retrieval passes
### A. Focal retrieval
Resolve exact entities, repos, components, projects and contracts named or implied by the objective.

### B. Structural expansion
Traverse only meaningful dependency/topology edges such as:
DEPENDS_ON, BLOCKED_BY, IMPLEMENTS, PRODUCES, CONSUMES, SUPERSEDES, GOVERNED_BY, VALIDATED_BY, OWNED_BY, MEMBER_OF.

Do not let REFERENCES or DUPLICATE_OF inflate dependency context.

### C. Authority collapse
Collapse multiple historical versions into the current authoritative artifact plus concise lineage unless history is required.

### D. Conflict attachment
If authoritative-enough sources disagree, include the conflict. Retrieval does not resolve it silently.

### E. Context budget
Rank candidates by task relevance, authority, dependency necessity, evidence quality, and relevant recency.

## Artifact disposition
Every candidate artifact must exit as exactly one:
- REQUIRED
- SUPPORTING
- OPTIONAL
- CONFLICTING
- SUPERSEDED
- EXCLUDED
- UNRESOLVED

## Core invariant
The graph identifies what may matter. The Context Compiler decides what the task actually needs.

## Deep implementation
See `20_PHASE_5_6_DEEP_IMPLEMENTATION_SECTION.md`, `runbooks/PHASE_5_6_IMPLEMENTATION_RUNBOOK.md`, `implementation/phase5_6/`, and Claude Code contract `contracts/claude_code/PR-01-PHASE5-WORK-CONTEXT-COMPILER.contract.yaml`.
