# WorkContextCompiler Specification

## Purpose
Compile the minimum sufficient authoritative context for one task. The graph discovers candidates; the compiler decides inclusion.

## Inputs
- objective/task scope
- principal/namespace permissions
- Graphiti/Memory retrieval results
- canonical topology relations
- corpus candidate relations
- context/token budget

## Pipeline
1. Parse objective and resolve focal entities.
2. Retrieve canonical lexical/temporal/graph candidates.
3. Expand traversable structural edges with bounded depth.
4. Attach blockers, supersession lineage, conflicts and material Unknowns.
5. Hydrate canonical Memory records for evidence/provenance/confidence/lifecycle.
6. Collapse stale versions to current authority plus concise lineage.
7. Score inclusion necessity, not business priority.
8. Fit to context budget without dropping REQUIRED or CONFLICTING records.
9. Emit `WorkContextPacket` and exclusion ledger.

## Artifact dispositions
REQUIRED, SUPPORTING, OPTIONAL, CONFLICTING, SUPERSEDED, EXCLUDED, UNRESOLVED.

## Safety law
If the budget cannot fit all REQUIRED + CONFLICTING material, return BLOCKED_CONTEXT_BUDGET rather than silently truncate.
