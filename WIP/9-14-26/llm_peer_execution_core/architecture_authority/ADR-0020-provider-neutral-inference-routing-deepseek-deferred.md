# ADR-0020: Provider-Neutral Inference Routing; DeepSeek Deferred

- **Status:** Accepted
- **Date:** 2026-08-12
- **Decision owner:** L9 architecture
- **Law:** `PEER_EXECUTION_THIN_ADAPTER_LAW.yaml`

## Context

The immediate goal is to make the full pipeline work through Claude Code while preserving a low-friction path to cheaper or newer inference providers later. Building provider-specific architecture before the execution substrate is correct would compound the current adapter gap.

## Decision

Provider and model selection are runtime routing/configuration concerns, not canonical Program semantics.

For the current phase:

- Claude Code remains the active implementation provider path.
- DeepSeek integration is deferred.
- No DeepSeek-specific Program Execution code is added now.
- The architecture MUST nevertheless support a future Claude-Code-backed provider switch or direct provider binding without changing Program Controller semantics.

Inference budgets, model/provider observations, token usage, cache usage, and estimated cost are canonical telemetry/budget concepts owned upstream. Values that a provider cannot report remain `UNKNOWN`; they are never fabricated.

Secrets, provider endpoints, and credentials remain deployment/runtime configuration and MUST NOT enter canonical Program artifacts.

## Consequences

- Current work focuses on the execution spine rather than vendor integration.
- A future DeepSeek switch through Claude Code can be configuration if the host supports it.
- A future direct provider path can use a shared transport and thin provider adapter.
- Model-market churn does not force architecture churn.

## Rejected alternatives

### Implement DeepSeek immediately

Rejected for this phase because it would optimize the provider before correcting the shared execution substrate.

### Encode provider selection in canonical change IR

Rejected because provider choice is an execution decision, not software-change meaning.
