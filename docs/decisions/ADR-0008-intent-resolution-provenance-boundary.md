# ADR-0008: Intent resolution is an explicit provenance-bearing boundary

## Status

Accepted

## Date

2026-08-10

## Context

Minimal user intent necessarily leaves details unstated. Some can be discovered from repository evidence, some are determined by governance policy, some are reversible planning choices, and some represent genuine authority decisions.

If those categories are collapsed inside a model prompt, machine inference can silently become execution authority. The system also loses the ability to explain how a short user request became a large executable program.

A durable boundary is required between what the user requested and what the system concluded the request means.

## Decision

1. Introduce program-execution.intent-resolution.v1 and a canonical INTENT_RESOLUTION artifact.
2. Every material derived requirement must trace to one of:
    * explicit user intent;
    * verified evidence;
    * an accepted decision;
    * an active governing policy.
3. Resolution classifies unresolved questions as:
    * evidence-determined — resolve automatically from authoritative evidence;
    * policy-determined — resolve automatically from an explicit policy and preserve policy provenance;
    * reversible planning choice — choose autonomously within existing authority;
    * authority-bearing decision — do not infer; create a decision or scoped Unknown.
4. Unattributed model inference may inform search or planning but cannot become execution authority.
5. Resolution records confidence for target, authority, repository understanding, and normalized intent.
6. The resolved artifact is an input to program synthesis. It is not Controller runtime state.

## Options considered

1. Synthesize a Blueprint directly from the user prompt. Rejected: hides authority-producing inference.
2. Store reasoning only in logs or conversation history. Rejected: not a stable or machine-auditable contract.
3. Introduce a typed resolution intermediate representation. Chosen: provides provenance, replayability, and a clean compiler boundary.

## Consequences

### Positive

* A minimal request can produce a sophisticated program without becoming opaque.
* Authority-bearing gaps remain visible.
* Program synthesis can be deterministic over a normalized input.
* Human review can focus on decisions rather than implementation detail.

### Negative / costs

* Adds another schema and lifecycle artifact.
* Evidence freshness and provenance references must be maintained.
* Resolution quality becomes a first-class validation concern.

## Related

* ADR-0007 — goal-level intent front door
* ADR-0009 — named autonomy policy profiles
* ADR-0010 — Blueprint synthesis and Controller boundary
* DPK repository-truth and execution-package contracts
