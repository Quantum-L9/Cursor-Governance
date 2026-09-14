# Cursor-Governance Program Execution Handoff

## Boundary
The planner decides WHAT bounded program should exist and WHY. Cursor-Governance Program Execution decides HOW to execute it and owns campaign state until terminal convergence.

## Required handoff
- plan_id/version
- objective
- selected waves/work units
- prerequisite DAG
- per-WorkUnit authoritative artifacts and evidence refs
- completion criteria
- validation expectations
- risk/authority constraints
- unresolved Unknowns
- explicit out-of-scope work
- reconsideration triggers
- source graph/corpus snapshot identities

## Program Execution must not
- reinterpret candidate relations as canonical dependencies without evidence
- expand scope to deferred WorkUnits without a new plan revision or authorized campaign rule
- mutate Dropbox source artifacts as part of planning

## Return receipt
Program Execution should return per WorkUnit: terminal state, commits/PRs, validation evidence, blockers, discovered dependency changes, architecture decisions, and new corpus facts worthy of reinjection.

## Implementation boundary
The Phase 6 build contract terminates at a schema-valid Program Execution handoff. Cursor-Governance remains the sole owner of campaign execution, scheduling, workers, CI, retries and convergence.
