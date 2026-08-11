# ADR-0012: Replan revisions are evidence-triggered and independently validated

## Status

Accepted

## Date

2026-08-10

## Context

Bounded authority alone does not guarantee good replanning. A worker could misdiagnose a failure, propose unnecessary work, or repeatedly mutate its plan based on its own unsupported assumptions.

Program Execution already separates worker claims from independent verification. Replanning must preserve the same separation of duties.

A replan should therefore be a first-class, inspectable state transition, not an invisible prompt rewrite.

## Decision

1. Every replan is represented as a digest-bound Replan Revision referencing:
    * Program Lock digest;
    * previous runtime/plan revision;
    * trigger evidence;
    * affected future execution units;
    * proposed delta;
    * authority-containment result;
    * expected validation effect.
2. Replanning is triggered by verified state or evidence, not solely by a worker assertion.
3. The component proposing a material replan does not independently approve that same replan.
4. Before activation, an independent verifier checks:
    * evidence sufficiency;
    * Program Lock containment;
    * dependency integrity;
    * permission non-widening;
    * retained acceptance/gate obligations;
    * absence of rewritten historical evidence.
5. The Controller alone activates an accepted Replan Revision and advances the canonical runtime plan revision.
6. Replan validation failure preserves the previous valid plan and records the failure.
7. Repeated replan failure across the same cause becomes an escalation signal rather than an infinite repair loop.

## Options considered

1. Let workers rewrite future prompts informally. Rejected: no durable evidence or authority boundary.
2. Let the Controller accept any syntactically valid replan. Rejected: does not establish semantic correctness or separation of duties.
3. Use evidence-bound proposals plus independent validation. Chosen: applies the existing proof model to adaptive planning.

## Consequences

### Positive

* Replanning becomes auditable and replayable.
* Failed replans do not corrupt the last valid execution plan.
* Autonomy can grow without making worker self-assessment authoritative.
* Replan loops can be measured and governed.

### Negative / costs

* Adds receipts/revisions and verifier work.
* Some replans incur additional latency.
* Replan schemas require lifecycle and compatibility rules.

## Related

* ADR-0011 — bounded replanning within Program Lock
* ADR-0016 — durable typed runtime state
* environment/program-execution/conformance/
