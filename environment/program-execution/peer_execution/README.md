# Peer Execution Core

Canonical shared execution substrate for Program Execution `worker_host` providers.

Authority direction:

```text
Program Controller
  -> Peer Runtime Binding
  -> Execution Profile
  -> Peer Execution Core
  -> Shared Transport
  -> Thin Provider
  -> Host / model / IDE / API
```

`peer_execution/` owns lifecycle mechanics, capability-receipt freshness, context
manifest construction, canonical permission policy, execution budgets, provider
telemetry normalization, and Program-facing terminal receipt construction.

A thin provider owns only provider availability, request translation, invocation,
poll/cancel translation when supported, and translation of host output into
`CanonicalProviderResult`.

Provider code MUST NOT own Program state, leases, worktrees, canonical receipts,
independent verification, identity resolution, autonomy policy, memory semantics,
or convergence.

## Public front door (the only live entry)

`peer_execution.front_door.execute(PeerExecutionRequest)` is the one public
operation through which live campaign execution enters Peer Execution. It owns
binding resolution, the capability probe, dispatch, provider retry/failover
classification and result normalization, and it returns a provider claim,
never a Controller verdict. `scripts/run_peer_task_pipeline.py` is an operator
facade whose helpers are thin internal aliases over it.

Failure classes and what the front door does about them:

| Class | Meaning | Action |
|---|---|---|
| `SAFE_BEFORE_DISPATCH` | no dispatch id exists yet (resolve/probe/prepare failed) | alternate provider within `EXECUTION_FAILOVER_POLICY.yaml` |
| `KNOWN_TERMINAL` | the provider confirmed its window ended | retry of a mutating contract only after the caller proves the prior Controller attempt fenced |
| `AMBIGUOUS_SIDE_EFFECT` | timeout with unconfirmed termination, connection lost after dispatch | never retried or failed over: `PROVIDER_FAILOVER_UNSAFE` |

Program, lock, task, contract, lease and Controller attempt identity never
change across a failover; provider ref and provider execution id do. Every try
is recorded in `runtime/peer-execution/retry-receipts/`, and that record is
fail-closed: a receipt that cannot be written raises
`RetryReceiptUnrecorded` (the claim rides the exception for diagnostics) rather
than returning a claim with an empty `retry_receipt`. A `collect` failure after
a confirmed `PASS` is classified `KNOWN_TERMINAL` at stage `collect` (status
`UNKNOWN`, never retried or failed over here; `PROVIDER_FAILOVER_UNSAFE` for a
mutating contract) instead of escaping the lifecycle. Provider health is
advisory ordering only: a stale healthy record never bypasses a live probe and
a stale unhealthy one never blacklists a provider.
