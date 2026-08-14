<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/ADAPTER_CONTRACT.md
layer: contract
owner: governance-control-plane
status: active
version: 2.0.0
updated: 2026-08-12
/L9_META -->

# Agent surface adapter contract

Every agent surface adapter is thin. Claude Code is not a gold-standard thick
adapter and no peer catches up by copying Claude implementation.

## Surface responsibilities

A surface adapter may carry only surface discovery/bootstrap, memory endpoint
configuration, identity environment examples, and references to canonical
shared policy. It MUST NOT own Program lifecycle, scheduler logic, autonomy
policy, memory semantics, execution budgets, canonical receipts, or duplicated
execution machinery.

## Memory carrier

Cloud Graphiti endpoint:

```text
https://memory.quantumaipartners.com/graphiti/mcp
```

Authentication uses `GRAPHITI_MCP_TOKEN`. Writer identity is separate and comes
from `agent_registry.yaml` through `USER_ID`, `L9_MEMORY_AGENT_ID`, and
`L9_MEMORY_SOURCE`. Surface adapters never invent a second `agent_id`.

## Executable peer carrier

Execution topology lives only in `environment/agents/PEER_RUNTIME_BINDINGS.yaml`.
Each binding declares:

```yaml
surface: claude-cli
provider_ref: claude-code-direct
execution_profile_ref: worker-default
```

`agent_ref` belongs to the peer entry, not the provider descriptor. Program
Execution resolves the binding, applies the execution profile, and invokes the
provider through `environment/program-execution/peer_execution/`.

Provider-specific Program modules are thin. Shared lifecycle, permissions,
context, budgets, transports, telemetry, receipts, and admitted-dispatch
concurrency live upstream.

## Autonomy

Root `autonomy/` is the canonical authorization/control plane and never owns
Program state. Shared bounded-concurrency mechanics live at
`environment/program-execution/peer_execution/autonomy/`, not under a provider adapter.

## Validation

```bash
make agents-env
make agents-runtime-bindings-validate
make program-execution-adapters
make program-execution-conformance
make peer-execution-validate
make peer-execution-probe
make peer-execution-conformance
```

Thin-provider violations are merge-blocking.
