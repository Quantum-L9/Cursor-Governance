# Program Execution

Program Execution is the serial authority plane for executable programs. Peer
and model providers connect through one shared Peer Execution Core.

- `core/`: Program truth, Program Locks, readiness, leases, task state,
  verification, canonical receipts, and convergence.
- `peer_execution/`: canonical provider request/result contracts, context,
  profiles, permissions, lifecycle, shared transports, telemetry evidence, and
  terminal receipt normalization.
- `adapters/`: thin provider or external-system translation only.
- `integrations/`: bridges to existing runtimes without copying authority.
- `registry/`: provider registry, execution profiles, routing, concurrency,
  health, and failover.
- `conformance/`: fail-closed architecture and behavioral checks.
- `campaigns/`: immutable campaign seeds plus landing policy
  (`CAMPAIGN_EXECUTION_POLICY.yaml` — one integration branch per campaign;
  `PR_REMEDIATE=0 make pr`; no remediate; no merge; no PRs against `main`).

Canonical peer topology lives only in
`environment/agents/PEER_RUNTIME_BINDINGS.yaml`:

```text
agent_ref + surface -> provider_ref + execution_profile_ref
```

A provider descriptor is identity-neutral. It MUST NOT carry `agent_ref`, own
Program state, author policy defaults, construct canonical receipts, or copy
scheduler/autonomy/memory behavior.

The binding law is registered at
`environment/contracts/execution/PEER_EXECUTION_THIN_ADAPTER_LAW.yaml`.

Mutable runtime belongs under `$HOME/.l9/`, never this source tree.
