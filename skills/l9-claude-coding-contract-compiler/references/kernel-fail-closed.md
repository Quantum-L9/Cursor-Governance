<!-- L9META
parent: l9-claude-coding-contract-compiler
layer: reference
role: failclosedkernel
version: 1.0.0
updated: 2026-07-12
sources: Pr-B-Contract.md (sections 12, 19, 29)
-->

# Fail-Closed Kernel  (BINDING — always active)

## Prime Directive
When evidence is missing, malformed, or ambiguous, the contract must BLOCK, never pass.
Absence of proof is proof of failure.

## Blocking States (any of these BLOCKS a required gate)
missing, malformed, mismatched, skipped, cancelled, timed_out, action_required,
unknown_outcome, duplicate_conflict, bad_content_hash, absent_content_hash,
subject_mismatch, base_mismatch, repository_mismatch, policy_digest_mismatch.

## Decision Precedence
```
control_plane_corruption  >  required_gate_failure  >  legacy_required_failure  >  normal_pass
```
Control-plane corruption blocks regardless of gate mode (blocking/advisory/shadow).

## Mode Semantics
- blocking: only `passed` satisfies promotion; all else blocks.
- advisory: normal fail/error is advisory; evidence corruption still blocks.
- shadow: normal outcome does not block; evidence corruption still blocks.
- unselected: absence expected; unexpected valid/malformed evidence blocks.

## Integrity Checks (per result, all required)
canonical schema, content hash, gate id, owner layer, gate mode, lifecycle, subject repo,
subject sha, base sha, event type, plan digest, registry semantic digest, risk digest,
rule-mode digest, base schema, base gate id, base result/outcome consistency, allowed value.

## Structured Failure Evidence
Every stage crash MUST emit structured evidence, never a silent exit:
- planning failure -> blocked decision with `controlplaneerrors: [gate_plan_missing]`
- registry failure -> `controlplaneerrors: [gate_registry_invalid]`
- executor crash -> execution-state record, NOT a fake base result
- artifact unavailable -> `controlplaneerrors: [gate_result_artifact_unavailable]`
The final promotion step MUST NOT fail before writing `promotion-decision.json`.

## Exit Codes
0 = promotion passed | 1 = promotion blocked | 2 = invocation failure before decision.
Minimize exit 2 by serializing a blocked decision for recoverable input failures.

## Failure Policy (governance)
missing/malformed policy, plan, evidence; hash/policy/subject mismatch; legacy required
missing; test failure; scope violation; remote change without approval -> `fail`.
promotionReady stays false until human approval is recorded.
