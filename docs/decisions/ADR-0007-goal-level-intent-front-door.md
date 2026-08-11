# ADR-0007: Goal-level intent is the Program Execution front door

## Status

Accepted

## Date

2026-08-10

## Context

Program Execution can execute a sealed program with bounded authority, but requiring a user to provide task decomposition, architecture context, validation commands, dependency graphs, rollback instructions, or worker prompts moves compiler responsibility back to the human.

The intended operator experience is outcome-level: the user states what should be achieved and, when necessary, identifies the target. Repository truth, governing policy, accepted decisions, implementation decomposition, validation, and execution sequencing should be discovered or compiled from authoritative sources.

Simplifying syntax alone is insufficient if the user must still understand the internal execution model.

## Decision

1. Introduce program-execution.intent.v1 as the canonical human-facing entry contract for new Program Execution work.
2. The minimum intent carries an objective and only target or policy information that cannot be resolved safely from context.
3. User input expresses desired outcome and optional narrowing constraints. It does not prescribe tasks, files, waves, worker prompts, test commands, or implementation strategy.
4. Missing discoverable information is resolved downstream rather than requested from the user.
5. Missing authority-bearing information is never guessed; it becomes an explicit decision or scoped Unknown.
6. RUN_REQUEST remains the execution front door for an already-compiled program. program-execution.intent.v1 is the front door when a program must first be created, extended, or superseded.

## Options considered

1. Keep rich Program Execution requests. Rejected: preserves unnecessary human orchestration burden.
2. Accept unconstrained natural language directly into the Controller. Rejected: mixes interpretation, authority creation, and runtime execution.
3. Use minimal intent followed by explicit resolution and synthesis. Chosen: minimizes user input while preserving typed authority boundaries.

## Consequences

### Positive

* Normal program initiation becomes goal-level rather than implementation-level.
* User input can remain small as execution architecture becomes more sophisticated.
* Internal schemas may evolve without expanding the human-facing contract.
* Clarification is reserved for genuine authority boundaries.

### Negative / costs

* Intent resolution becomes a governed compiler responsibility.
* Target and authority discovery require deterministic evidence sources.
* Sparse input requires stronger provenance and ambiguity handling downstream.

## Non-goals

* This ADR does not authorize the intent layer to execute work.
* It does not allow natural-language inference to create permissions or accepted architecture.

## Related

* ADR-0008 — intent resolution provenance boundary
* ADR-0009 — named autonomy policy profiles
* ADR-0010 — Blueprint synthesis and Controller boundary
* environment/program-execution/
* CANONICAL_LAW.md §2.1
