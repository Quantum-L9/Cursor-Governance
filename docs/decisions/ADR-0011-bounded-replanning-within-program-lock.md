# ADR-0011: Autonomous replanning is bounded by the immutable Program Lock

## Status

Accepted

## Date

2026-08-10

## Context

A long-running program will discover facts that were not available when its initial execution plan was synthesized. Requiring a human to rebuild the program after every unexpected dependency, failed implementation strategy, or newly discovered local condition unnecessarily shortens autonomy chains.

Unbounded replanning is not acceptable either. A runtime planner must not reinterpret a new obstacle as permission to change the objective, architecture, public contracts, risk acceptance, or execution permissions.

The stable boundary is the accepted Program Lock.

## Decision

1. Introduce bounded replanning under program-execution.replan.v1.
2. The Program Lock remains immutable and defines the maximum authority envelope for every replan.
3. Replanning may autonomously:
    * choose a different reversible implementation strategy;
    * reorder execution where existing dependency and gate law permits;
    * split an approved task into derived child execution units whose combined authority does not exceed the parent;
    * add diagnostics or verification probes;
    * create scoped runtime Unknowns;
    * resolve Unknowns from authoritative evidence;
    * retry failed work using a different compliant path.
4. Replanning may not autonomously change:
    * program objective;
    * accepted architecture or public contracts;
    * authority ownership;
    * materially authorized target set;
    * authorization ceiling;
    * accepted risk or waiver policy;
    * mandatory convergence gates;
    * final convergence authority.
5. Completed attempts, evidence, verification receipts, and gate receipts are immutable historical facts and are never rewritten by a replan.
6. Work that cannot fit inside the Program Lock requires a superseding Blueprint and new Program Lock.

## Options considered

1. Freeze the original task plan completely. Rejected: causes avoidable human intervention when reality differs from the initial plan.
2. Allow the agent to rewrite the program dynamically. Rejected: collapses planning and authority.
3. Allow derived planning changes only inside the locked envelope. Chosen: extends autonomy without expanding mandate.

## Consequences

### Positive

* Recoverable surprises no longer end autonomous execution.
* Replanning remains mechanically distinguishable from authority changes.
* Program Lock remains the stable trust anchor.
* Long chains can adapt without rewriting history.

### Negative / costs

* The Controller needs an explicit derived plan-revision model.
* Parent/child authority containment must be machine-checkable.
* Some discoveries will still require program-owner escalation.

## Related

* ADR-0012 — evidence-gated replan revisions
* ADR-0016 — durable typed runtime state
* Program Lock and Controller contracts
