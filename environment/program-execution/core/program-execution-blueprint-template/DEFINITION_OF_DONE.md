# Definition of Done: {{PROGRAM_NAME}}

The Execution Program is complete only when every applicable blocking condition is proven with evidence.

## Definition integrity

- The Blueprint validates with no unresolved placeholders or cross-reference errors.
- Every execution target, authority, decision, Unknown, risk, waiver, task, gate, and evidence record has one stable ID.
- No definition state is confused with runtime state or evidence result.

## Authority and contracts

- Every persistent fact and executable behavior has one authoritative owner.
- Competing or superseded authority paths are removed, disabled, or explicitly bounded.
- Cross-surface contracts name producer, consumer, version, compatibility, failure, replay, and ownership behavior.

## Execution and validation

- Every required task is `COMPLETED` or explicitly cancelled by accepted decision.
- Every blocking convergence gate has a valid Controller Gate Evaluation of `PASS`.
- Worker claims exactly match Controller-observed changed files and validations.
- Before any push or PR admission, local `make pr` / `make pr-check` (changed-files Core-CI mirror) has PASS evidence (`EVID` of type `local_pr_gate`). Remote CI is confirmation; PR remediation is exceptional (LL-003 / AGENTS.md §6).
- Lock/pin alignment (`uv lock --check` / toolchain SSOT) is PASS or N/A before mutating waves when Phase 0 requires it (LL-004).
- Failure, timeout, retry, duplicate delivery, replay, malformed input, authorization, rollback, and recovery paths are proven where applicable.

## Phase 0 and autonomy rail

- When `program_deploying: true`, `PHASE0_USER_CONFIG.yaml` has `phase0_complete: true` before mutating waves.
- Mid-flight stops are business-logic decisions or hard safety only; environmental/advisory CI was cleared in Phase 0.
- `autonomous_merge` remains false; human merge/publish/deploy stay denied unless separately authorized outside this pack.

## Operations and closure

- Observability signals, alert routing, support ownership, and recovery are operational.
- Cutover or destructive actions occurred only under exact approval.
- The Controller Handoff Receipt is accepted by the program owner.
- Residual risks are accepted by named owners.
- The final verdict is one of the canonical program verdicts.
