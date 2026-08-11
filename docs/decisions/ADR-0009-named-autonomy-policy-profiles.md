# ADR-0009: Named autonomy profiles own default execution authority

## Status

Accepted

## Date

2026-08-10

## Context

A simplified user interface cannot require users to restate ten permission flags, verification behavior, replanning rules, escalation rules, and Unknown handling on every request.

Hard-coding these defaults inside individual agents is worse: Claude Code, Cursor, ChatGPT, Codex, or another peer could then interpret the same intent under different authority.

Default autonomy must therefore be explicit, versioned, shared, and independent of the selected execution peer.

## Decision

1. Introduce versioned autonomy policy profiles, beginning with quantum-l9.safe-autonomy.v1.
2. A minimal intent references a policy profile rather than enumerating low-level permissions.
3. The profile owns default:
    * permission ceilings;
    * independent-verification requirements;
    * decision auto-resolution classes;
    * Unknown behavior;
    * bounded-replanning policy;
    * escalation boundaries;
    * termination behavior.
4. User or repository overlays may narrow an active profile but may never widen it implicitly.
5. Any widening requires explicit authority and a traceable accepted decision.
6. Policy profiles live in a shared Program Execution or adapter-neutral governance home. They are never defined independently inside Claude, Cursor, Codex, ChatGPT, or another peer.
7. Every peer consumes the same semantic policy revision.

## Options considered

1. Require permissions on every request. Rejected: defeats minimal-input UX and encourages inconsistency.
2. Let each peer define sensible defaults. Rejected: creates divergent authority and peer-specific behavior.
3. Use named canonical policy profiles. Chosen: compact user input with explicit, auditable authority.

## Consequences

### Positive

* Users select an autonomy posture rather than managing individual permission bits.
* Authority remains reviewable even when user input is tiny.
* Cross-peer behavior derives from the same policy source.
* Future autonomy improvements can be versioned independently from the intent schema.

### Negative / costs

* Policy versioning becomes compatibility-sensitive.
* Policy changes require peer conformance validation.
* A profile registry and provenance mechanism are required.

## Related

* ADR-0007 — goal-level intent front door
* ADR-0013 — canonical peer semantics
* ADR-0014 — atomic all-peer semantic revisions
* CANONICAL_LAW.md §2.1
