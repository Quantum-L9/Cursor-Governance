# Work Unit + Leverage Planning Playbook

## Objective
Transform graph-backed artifacts into bounded executable work units, then prioritize and group them into build waves that maximize downstream unlock per bounded effort.

## WorkUnit contract
Each WorkUnit should include:
- work_unit_id
- title
- objective
- evidence_refs
- artifact_ids
- current_state
- prerequisites
- dependents
- blockers
- capabilities_unlocked
- readiness evidence
- effort class + confidence
- risk class + confidence
- leverage dimensions
- unresolved unknowns

## Leverage dimensions
Score ordinally first, 0-5:
- dependency centrality
- unblock fan-out
- capability unlock
- reuse potential
- strategic alignment
- readiness
- effort
- risk
- unknown burden

## Priority classes
Prefer classes over fake precision:
- FOUNDATIONAL_UNLOCK
- QUICK_HIGH_LEVERAGE
- DEPENDENCY_REQUIRED
- READY_VALUE
- STRATEGIC_BET
- WAITING
- LOW_RETURN
- OBSOLETE
- UNKNOWN

## Counterfactual unlock analysis
For each candidate WorkUnit:
1. hypothetically mark complete
2. remove its blocking/dependency constraints where appropriate
3. recalculate newly executable/reachable WorkUnits
4. measure new capabilities and downstream unblocks

Use this to compare opportunity radius, not just textual importance.

## BuildWavePlan
Output waves, not a flat ranked list:
- Wave 0: authority ambiguity / prerequisites
- Wave 1: foundational unlocks
- Wave 2: dependent components now unblocked
- Wave 3: integrations
- Deferred: low-return, speculative, obsolete, blocked

Parallelize WorkUnits that do not depend on each other.

## Handoff invariant
The planner decides what bounded program should exist and why. Cursor-Governance Program Execution owns execution, scheduling, workers, CI, retries and convergence.

## Deep implementation
Reference implementation: `implementation/phase5_6/leverage_planner.py`. Build contract: `contracts/claude_code/PR-03-PHASE6B-LEVERAGE-PLANNER.contract.yaml`.
