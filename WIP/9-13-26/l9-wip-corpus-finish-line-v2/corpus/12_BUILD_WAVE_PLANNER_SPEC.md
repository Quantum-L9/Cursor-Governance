# BuildWave Planner Specification

## Objective
Transform prioritized WorkUnits into dependency-correct waves that maximize unlock density while preserving explicit uncertainty.

## Wave algorithm
1. Remove OBSOLETE units from active planning but retain them in history.
2. Isolate externally BLOCKED/UNKNOWN units.
3. Build prerequisite DAG from canonical dependencies.
4. Identify smallest upstream units with greatest downstream unblock fan-out.
5. Group independent ready units into parallel lanes.
6. Respect risk/authority constraints and required sequencing.
7. Recalculate reachability after each hypothetical wave completion.
8. Emit wave purpose, prerequisites, parallel groups, expected unlocks, evidence, and reconsideration triggers.

## Default waves
- Wave 0: authority/ambiguity/precondition repair
- Wave 1: foundational unlocks
- Wave 2: newly unblocked dependency work
- Wave 3: integrations/productization
- Deferred: waiting, low-return, strategic bets, unknowns

## Replanning trigger
Replan when canonical dependencies, blockers, readiness evidence, strategic objective, or material Unknowns change. Do not replan merely because a file timestamp changes.

## Deep implementation
Reference implementation: `implementation/phase5_6/build_wave_planner.py`. Build contract: `contracts/claude_code/PR-04-PHASE6C-BUILD-WAVES-PE-HANDOFF.contract.yaml`.
