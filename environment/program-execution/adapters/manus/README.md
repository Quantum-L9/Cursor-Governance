<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/program-execution/adapters/manus/README.md
layer: program-execution-adapter
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-08-10
/L9_META -->

# Manus Program Execution adapter (`manus-cloud`)

Worker-host execution adapter for the `manus` agent identity (role
`researcher-builder`, `environment/agents/agent_registry.yaml`). Peer of the
Manus **surface** adapter at `environment/agents/adapters/manus/`.

Manus is a cloud surface with no automated Controller execution transport, so
this adapter uses the **manual-handoff** provider model (the same honest model
as `chatgpt-manual-handoff`): it is only enabled when an explicit transport
flag and an external producer identity are present. Its authority is research
plus explicitly permitted artifact production, matching the
`researcher-builder` role.

## Status: dormant (honest coverage)

The probe reports `BLOCKED` unless `L9_MANUS_MANUAL_HANDOFF=1` and an external
`producer_identity` are supplied. The peer is registered for explicit coverage
rather than being silently absent.

| Contract | Value |
|---|---|
| adapter_kind | `worker_host` |
| provider.type | `manual_handoff` |
| actions | `inspect`, `artifact_production` |
| identity.binding | `agent_registry` (`manus`) |
| receipts | canonical lifecycle + `attempt` terminal |

## Promotion path

1. Provision a Manus handoff transport (envelope out / result in).
2. Implement the dispatch/collect bridge in `driver.py`, mirroring
   `adapters/chatgpt/`.
3. Flip `status.default` to `conditional` in `ADAPTER.yaml` once the transport
   is live.
