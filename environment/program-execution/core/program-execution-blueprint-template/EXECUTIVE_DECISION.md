# Executive Decision: {{PROGRAM_NAME}}

## Decision

REPLACE_WITH_THE_CANONICAL_DECISION_IN_PLAIN_LANGUAGE.

## Problem being resolved

REPLACE_WITH_VERIFIED_CURRENT_PROBLEM_AND_EVIDENCE_IDS.

## Target state

REPLACE_WITH_THE_END_STATE, SYSTEM_BOUNDARIES, AND AUTHORITATIVE OWNERS.

## Authority assignment

Reference `AUTHORITY_REGISTRY.yaml`; do not duplicate or contradict it here.

## Forbidden end states

- competing authority or duplicate execution paths;
- silent fallback, bypass, or success substitution;
- unversioned, unauditable, or unrecoverable state;
- runtime permission wider than the approved Task Card ceiling.

## Failure behavior

REPLACE_WITH_VISIBLE, RETRYABLE, RECOVERABLE, OR TERMINAL FAILURE SEMANTICS.

## Safe execution order

1. Refresh current-state evidence.
2. Resolve blocking decisions and Unknowns.
3. Prove foundational contracts and dependencies.
4. Execute additive or reversible changes.
5. Validate shadow, compatibility, migration, and failure paths.
6. Cut over only after named gates and exact approvals pass.
7. Retire superseded paths and install drift guards.

## Supersession rule

A new accepted decision must name the superseded decision, affected authority records, tasks, gates, migration impact, and rollback implications. Historical evidence remains immutable.
