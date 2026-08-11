# ADR-0016: Long autonomous chains run from durable typed state, not accumulated conversation

## Status

Accepted

## Date

2026-08-10

## Context

Long autonomy chains degrade when correctness depends on an agent remembering the complete preceding conversation. Context grows, stale assumptions remain in prompts, evidence and decisions become hard to distinguish, and a resumed worker may reconstruct state differently from the original worker.

Program Execution already has durable program state and canonical receipts. The new intent and replanning architecture should extend that principle rather than making larger prompts.

Agent episodic memory remains useful for continuity and lessons, but it is not Program Execution authority.

## Decision

1. Long-running execution is grounded in durable typed state.
2. Canonical execution state includes, as applicable:
    * original and normalized intent;
    * Intent Resolution;
    * immutable Program Lock;
    * current accepted Replan Revision;
    * decision state;
    * Unknown state;
    * risk and waiver state;
    * evidence ledger;
    * Attempt Receipts;
    * Verification Receipts;
    * Gate Receipts;
    * active peer semantic revision.
3. Every worker attempt receives a freshly rendered, minimal execution contract derived from current canonical state.
4. Workers are not expected to retain or replay the full prior conversation.
5. Context rendering includes only the authority, evidence, constraints, relevant history, and acceptance obligations required by that attempt.
6. Historical receipts remain addressable but are summarized unless directly relevant.
7. Graphiti/agent episodic memory may provide supplemental recall, lessons, and discovery hints but may not override Program Lock, typed runtime state, current evidence, or accepted decisions.
8. Resume after interruption reconstructs execution from durable state and digests, not from conversational memory.
9. The autonomy quality metric is independently verified useful progress per human intervention, not raw uninterrupted agent step count.

## Options considered

1. Keep expanding the running prompt. Rejected: context cost and stale-state risk grow with chain length.
2. Rely on agent episodic memory as runtime state. Rejected: memory is not the Program Execution authority model.
3. Persist typed state and render fresh per-attempt context. Chosen: supports long, resumable, evidence-grounded execution.

## Consequences

### Positive

* Autonomy chains can grow without proportional prompt growth.
* Worker replacement or restart does not lose authoritative execution state.
* Replanning operates over explicit current state instead of reconstructed narrative.
* Context can become smaller as the program becomes more sophisticated.

### Negative / costs

* Typed state schemas and migration rules must remain stable.
* Context rendering becomes a critical shared capability.
* Incorrect state projection must be caught by conformance testing.

## Related

* ADR-0002 — memory is an enforced contract, not advisory context
* ADR-0005 — one agent episodic memory; product/domain memory is out of band
* ADR-0006 — single memory front door
* ADR-0011 — bounded replanning within Program Lock
* ADR-0012 — evidence-gated replan revisions
* environment/program-execution/core/
