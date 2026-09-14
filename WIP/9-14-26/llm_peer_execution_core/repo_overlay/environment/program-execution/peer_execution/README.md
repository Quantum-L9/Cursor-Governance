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
