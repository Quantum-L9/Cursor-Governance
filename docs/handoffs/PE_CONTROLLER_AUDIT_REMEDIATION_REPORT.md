# Program Execution and Controller Audit Remediation Report

**Repository:** `Quantum-L9/Cursor-Governance`  
**Branch:** `fix/pe-smoke-controller-test-support`  
**Scope:** `environment/program-execution`, the Program Execution Controller template, campaign execution, and Peer Execution.  
**Excluded scope:** Coding Constellation and external control-plane dependencies remained deferred and were not introduced.

## Executive Summary

The Program Execution Controller and surrounding execution paths were audited for authority drift, stale tests, unsafe retry behavior, persistence divergence, and public routes that could mutate execution state outside Controller authority. The resulting repairs make canonical SQLite state authoritative for campaign status, bind retry verification to the exact baseline and Git head of the current execution attempt, reject expired or malformed leases at every lifecycle transition, validate integration-receipt lineage before fan-in, and make controller mutation/event pairs atomic.

The campaign and Peer Execution layers were also hardened. Live direct-source resumes bind the submitted source document rather than silently substituting the host copy; activation resumes continue to reconcile their persisted host source. Unsafe replay writers are disabled, compiler preflight rejects program documents that cannot be lowered, dormant providers cannot be routed for execution, pre-dispatch provider exceptions are classified and safely fail over, and terminal provider codes are preserved for deterministic retry policy. All repairs were validated with focused regressions, the full controller certification, smoke certification, core validation, and expanded conformance.

## Findings and Repairs

| Area | Verified issue | Repair | Regression coverage |
|---|---|---|---|
| Controller test boundary | Stand-alone controller test modules could not consistently import shared helpers under pytest importlib mode. | Added the controller test `conftest.py` import boundary. | `make pe-smoke`; full controller suite. |
| Campaign status authority | `campaign-status.json` could diverge from the canonical state database and bootstrap writes were not fully projected. | Made `campaign_status` canonical in `StateDB`; post-commit materialization reconciles the JSON projection. | Campaign status and legacy reconciliation tests. |
| Lease authority | Non-positive lease lifetimes were accepted and lifecycle transitions did not consistently reject expired or malformed leases. | Require a positive TTL and enforce live, parseable lease expiry for prepare, start, submit, verify, and completion transitions. | Lease/approval tests and recovery fixture. |
| Attempt attribution | A retry baseline did not include the Git head, allowing prior committed work to be credited to a later retry. | Persist baseline head and compute effects against both file baseline and the attempt head. | Attempt tests, verification lifecycle tests, and persistence convergence tests. |
| Fan-in integrity | Integration receipts could be overwritten or projected without validating receipt lineage. | Fail closed on duplicate artifacts and validate canonical receipt/task/contract/program lineage before integration. | Campaign fan-in tests. |
| Atomic authority writes | Several controller state mutations were not consistently paired atomically with their ledger event and projection. | Wrapped dispatch binding, lease release, approval, unknown-state, halt, and receipt changes in controller transactions; materialize projections after commit. | Persistence fault-injection regression tests. |
| Governance wiring | Runtime-created wiring symlinks were counted as worker effects by attempt baseline comparison. | Exclude governance wiring paths from baseline-derived observed effects as they are already excluded from controller change detection. | Kernel verdict wiring test. |
| Reason-code drift | Newly emitted controller error codes were absent from the controller taxonomy. | Registered lease and integration-lineage codes in `pec.reasons`. | Taxonomy completeness test. |
| Live resume provenance | A direct `campaign-source.v2` submission could resume using a different host source; missing source was allowed as `NO_SOURCE`. | Bind a direct invocation to its submitted source, require source provenance, and retain persisted-host reconciliation only for activation/plan inputs. | Campaign resume repair tests and active-runtime tests. |
| Compiler schema/lowering gap | The source schema accepted program documents missing fields that the lowering implementation indexes directly. | Added deterministic preflight completeness checks for every lowering-required Program field. | Compiler completeness regression. |
| Replay routes | `campaign materialize` and `campaign reset` could write worktrees, retire runtime state, or rewind branches outside a Controller recovery receipt. | Disabled both writers with explicit Controller-recovery guidance and updated stale success-path tests to assert no mutation. | Replay route tests. |
| Peer routing | Dormant providers were instantiated by the execution front door, generic probe/dispatch exceptions escaped classification, and terminal codes were discarded. | Reject dormant/non-routable providers at execution routing, classify raw pre-dispatch errors as safe failures, preserve terminal codes, and fail closed for unclassified terminal outcomes. Inventory probing remains able to instantiate dormant adapters. | Peer front-door, probe-command, and provider-profile regressions. |
| Test-target drift | The controller target documentation embedded stale test counts; an isolated test had no executable module entry point. | Replaced numeric claims with matcher-based wording and added the missing `unittest.main()` entry point. | Full controller certification. |

## Validation Evidence

| Command | Result |
|---|---|
| `make program-execution-controller-tests` | Passed after repairing all verified controller failures. |
| `make pe-smoke` | Passed: **52 tests**. |
| `make program-execution-core-validate` | Passed, including core pair validation, campaign schema checks, compiler tests, and promotion validation. |
| `environment/program-execution/scripts/run_conformance.py -j 4` | Passed: **925 tests**. |
| Focused campaign, replay, peer, lease, persistence, and source-resume suites | Passed during red/green remediation. |
| `git diff --check` | Passed before commit. |

## Local Commits

| Commit | Description |
|---|---|
| `cb0c6ab` | `fix(pe): make controller test helpers importable` |
| `af75330` | `fix(pe): harden controller and execution boundaries` |

No push, pull request, merge, deployment, Coding Constellation dependency, or external control-plane dependency was created.

## Remaining Deliberate Boundaries

The replay materialization and reset tools are intentionally unavailable until an explicitly Controller-owned recovery workflow exists. This is a safe restriction rather than a missing automatic recovery capability. Coding Constellation remains deferred and non-blocking, consistent with the declared architecture direction.
