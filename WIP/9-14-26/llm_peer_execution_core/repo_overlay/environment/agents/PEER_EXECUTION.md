<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/PEER_EXECUTION.md
layer: contract
owner: governance-control-plane
status: active
version: 4.0.0
updated: 2026-08-12
/L9_META -->

# Executable Peer Contract v4

> One Program Controller. One peer execution substrate. Many providers. Thin
> bindings. Zero copied brains.

## Authority chain

```text
agent_registry.yaml             WHO
PEER_RUNTIME_BINDINGS.yaml      WHICH surface/provider/profile
Program Controller              WHAT may execute and exact state
Peer Execution Core             HOW admitted provider execution runs
root autonomy                   MAY the leased operation occur
thin provider                   HOW this provider is invoked
provider / host                 WHERE work runs
```

Program Execution remains the serial authority plane. Peer Execution Core is
subordinate execution infrastructure and does not create a second scheduler or
Program state machine.

## Binding v2

`PEER_RUNTIME_BINDINGS.yaml` is the topology SSOT:

```yaml
claude-code:
  agent_ref: claude-code
  execution:
    required: true
    bindings:
      - surface: claude-cli
        provider_ref: claude-code-direct
        execution_profile_ref: worker-default
```

Provider descriptors are identity-neutral and MUST NOT contain `agent_ref`.
Provider substitution therefore does not change peer identity.

`execution.required: true` means at least one declared binding must be live and
READY. `false` may retain dormant future bindings without asserting readiness.

## Two readiness gates

Gate A proves a binding can currently accept Program work:

```text
(agent_ref, surface, provider_ref, execution_profile_ref) -> READY | BLOCKED
```

Gate B proves the selected provider can execute one exact Program-Lock-bound
contract. The provider capability receipt remains TTL-fresh and digest-bound.

## Peer Execution Core

Canonical path: `environment/program-execution/peer_execution/`.

It owns once for every peer/provider:

- lifecycle and capability-receipt mechanics;
- canonical execution request/result contracts;
- context manifest construction;
- permission profiles;
- inference and timeout budgets;
- shared subprocess/transport mechanics;
- telemetry/evidence normalization;
- canonical attempt/verification receipt construction;
- provider-neutral cancellation/status lifecycle.

Shared admitted-dispatch bounded concurrency lives at
`environment/program-execution/peer_execution/autonomy/` and is subordinate to Program admission.

## Thin provider law

A provider may only declare/probe capabilities, translate a canonical request,
invoke through an approved transport, poll/cancel when supported, and translate
provider output to `CanonicalProviderResult`.

Forbidden inside provider adapters include Program state, leases, scheduler
policy, generic context/prompt policy, budgets, retry/timeout policy, canonical
receipts, verification authority, autonomy policy, memory semantics, merge, and
deployment authority.

Binding law:
`environment/contracts/execution/PEER_EXECUTION_THIN_ADAPTER_LAW.yaml`.

## Current peer topology

| Peer | Surface | Provider | Profile | Required |
|---|---|---|---|---|
| Cursor | cursor-ide | cursor-foreground | worker-default | yes |
| Cursor | cursor-ide | cursor-background | worker-default | yes |
| Claude Code | claude-cli/web/mobile | claude-code-direct | worker-default | yes |
| Codex | codex-cloud | codex-cloud | worker-default | no |
| Gemini | gemini-cli | gemini-review | reviewer-default | no |
| Manus | manus-cloud | manus-cloud | worker-read-only | no |

The legacy Claude bounded provider is retired. Bounded execution is a shared
Peer Execution Core concern and is not modeled as a provider identity.

## Validation

`make peer-execution-conformance` composes identity, topology schema,
provider/adapter conformance, thin-provider law, Program Execution conformance,
and live binding readiness.
