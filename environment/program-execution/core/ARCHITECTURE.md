# Program Execution System Architecture

## Components

| Component | Owns | Must not own |
|---|---|---|
| Program Execution Blueprint | target state, authority, decisions, Unknowns, risks, targets, dependencies, waves, task definitions, authorization ceilings, gates, Definition of Done | mutable runtime state, leases, worker claims, repository HEAD, attempt verdicts |
| Program Execution Controller | immutable program lock, repository reconciliation, task runtime state, leases, rendered contracts, attempts, independent verification, recovery, runtime gate evaluations, handoff receipts | program intent, target-state meaning, authority reassignment, permission widening, silent waivers |
| Worker | one admitted attempt in one bounded execution context | verification authority, program advancement, permission interpretation, remote credentials by default |
| Program owner | accepts or supersedes decisions, grants exact approvals, accepts residual risk, declares final program verdict | retrospective evidence fabrication or silent alteration of historical receipts |

## State domains

The system has four separate state domains. They must never be collapsed into one overloaded `status` field.

1. **Definition state**: whether a Blueprint object is draft, active, superseded, or retired.
2. **Runtime task state**: whether a Controller projection is blocked, eligible, leased, executing, submitted, verifying, passed locally, failed, stale, cancelled, or completed.
3. **Evidence result**: PASS, FAIL, BLOCKED, UNKNOWN, or NOT_APPLICABLE_WITH_REASON.
4. **Program verdict**: CONVERGED, CONVERGED_WITH_NON_BLOCKING_RISKS, NOT_CONVERGED, or INCONCLUSIVE.

## Data flow

```text
Blueprint source files
  -> Blueprint validator
  -> immutable Program Lock
  -> runtime task projections
  -> exact Source Contract
  -> exact-state Rendered Contract
  -> worker Attempt Receipt
  -> independent Verification Receipt
  -> gate evaluations and task transition
  -> Controller Handoff Receipt
  -> program-owner acceptance or superseding Blueprint
```

## Failure law

Failure is explicit and evidence-bearing. A failure may block, stale, fail, cancel, or preserve an attempt for recovery. It must never be represented as success, silently retried outside policy, or bypassed by reproducing an upstream result in a downstream surface.
