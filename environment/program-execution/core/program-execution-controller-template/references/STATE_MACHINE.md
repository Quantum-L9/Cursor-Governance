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
FAILED -> EXECUTING or SUBMITTED to retry the same lease, contract, and worktree once the cause is fixed.
Retries are finite: `policy/risk-tiers.yaml` declares `max_attempts` per risk tier, and `pec start`
refuses a further retry once that many attempts are recorded, landing the task in CANCELLED with
`RETRY_BUDGET_EXHAUSTED` and releasing its lease. Under a live campaign integration branch a
dependency is satisfied only by COMPLETED (post fan-in), never by PASSED_LOCAL.
FAILED or STALE -> ELIGIBLE when a new lease and a fresh contract are required.
```

Definition states, evidence results, and program verdicts are not runtime task states.
