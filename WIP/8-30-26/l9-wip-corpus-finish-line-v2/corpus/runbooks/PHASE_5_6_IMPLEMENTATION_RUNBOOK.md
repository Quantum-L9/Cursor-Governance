# Phase 5–6 Implementation Runbook

## Preconditions
- Corpus pipeline post-remediation E2E gate passes.
- Graphiti Memory can return projection hits that hydrate canonical `MemoryRecord`s.
- Topology edge semantics and traversability are available to the caller.
- Current `l9-cognitive-runtime` main is clean and CI baseline green.

## Step 1 — Bind repository reality
1. Fetch current main and all repo-local AGENTS/ADRs/specs governing context compilation, memory integrations, execution contracts and package ownership.
2. Identify existing service/domain/port patterns. Do not create parallel architecture.
3. Record exact baseline SHA in each PR contract execution receipt.

## Step 2 — Implement Phase 5 port before logic
Create or reuse a narrow `GraphMemoryQueryPort` with only:
- resolve entities
- search candidates
- traverse canonical edges
- hydrate canonical records

No provider-specific Graphiti types may cross into the compiler domain.

## Step 3 — Implement WorkContextCompiler
Run in ordered passes:
1. focal entity resolution;
2. bounded canonical retrieval;
3. bounded structural traversal;
4. canonical hydration;
5. supersession collapse;
6. conflicts/Unknown attachment;
7. disposition classification;
8. deterministic budget packing;
9. packet validation.

Fail if REQUIRED + CONFLICTING content exceeds budget.

## Step 4 — Implement WorkUnitCompiler
Only synthesize work from evidence classes that can support a bounded objective:
- explicit open task/TODO/milestone;
- roadmap/plan/spec cluster;
- blocker/dependency chain;
- project candidate with evidence;
- capability gap tied to explicit objective.

Deduplicate by semantic work identity. Never merge merely because embeddings/topics are similar.

## Step 5 — Implement LeveragePlanner
Use ordinal dimensions first. Record the evidence that justified each value. Compute a priority class from rules, not arbitrary decimals. Counterfactual simulation must operate on a copied DAG and cannot mutate canonical work state.

## Step 6 — Implement BuildWavePlanner
- remove obsolete units from active waves but preserve history;
- isolate external blockers/Unknowns;
- topologically sort prerequisites;
- choose upstream unlocks;
- parallelize independent ready nodes;
- recalculate reachability after each hypothetical wave;
- emit reconsideration triggers.

## Step 7 — Emit Program Execution handoff
The handoff contains WHAT/WHY only. It must not contain worker scheduling, PR merge commands, provider routing or campaign loop state.

## Step 8 — Required test ladder
1. unit tests for every disposition and priority class;
2. property test: dependency traversal never follows `REFERENCES` or `DUPLICATE_OF` by default;
3. property test: budget never drops REQUIRED/CONFLICTING;
4. supersession-chain test;
5. conflict-preservation test;
6. unresolved endpoint test;
7. cycle detection in work-unit DAG;
8. counterfactual simulation immutability test;
9. build-wave parallelism test;
10. full fixture: graph-shaped input → WorkContextPacket → WorkUnit[] → BuildWavePlan → PE handoff.

## Step 9 — Acceptance fixture
Use one known real WIP objective and a frozen graph/memory fixture. Human-select the expected authoritative artifacts and dependency order before running the compiler. Compare:
- required artifact precision/recall;
- false inclusion rate;
- missed blockers;
- wrong supersession selection;
- work-unit coherence;
- wave dependency correctness.

## Step 10 — Promotion gate
Do not connect to Program Execution until:
- schemas validate;
- all Phase 5–6 tests pass;
- the real objective fixture passes;
- no direct provider/corpus writes exist;
- PE handoff validates against its schema;
- rollback is simply disable Phase 5–6 caller and retain existing canonical memory.
