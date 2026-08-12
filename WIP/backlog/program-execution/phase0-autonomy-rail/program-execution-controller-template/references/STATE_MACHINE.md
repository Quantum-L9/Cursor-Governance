# Runtime Task State Machine

```text
BLOCKED <-> ELIGIBLE -> LEASED -> PREPARED -> CONTRACTED -> EXECUTING -> SUBMITTED -> VERIFYING
                                                                               |          |
                                                                               |          +-> PASSED_LOCAL
                                                                               |          +-> FAILED
                                                                               |          +-> STALE
                                                                               +-> STALE

PASSED_LOCAL -> COMPLETED only when every Task Card completion gate passes and all required action receipts exist.
Any active state -> CANCELLED only through accepted program authority.
FAILED or STALE -> ELIGIBLE only after the cause is resolved, the target is reconciled, and a fresh contract is rendered.
```

Definition states, evidence results, and program verdicts are not runtime task states.

## Phase 0 gate

Long-running autonomy and the `program_deploy_max_autonomy` profile are not admitted until `PHASE0_USER_CONFIG.yaml` reports `completeness.phase0_complete: true` when `program_deploying: true`. Incomplete Phase 0 keeps tasks `BLOCKED` with error `PHASE0_INCOMPLETE`.

## Local PR gate before remote

Tasks that authorize push or pull_request must carry `local_pr_gate` PASS evidence before those actions are eligible. Skipping local `make pr` yields `LOCAL_PR_GATE_SKIPPED` (not an invitation to remediate on the PR).
