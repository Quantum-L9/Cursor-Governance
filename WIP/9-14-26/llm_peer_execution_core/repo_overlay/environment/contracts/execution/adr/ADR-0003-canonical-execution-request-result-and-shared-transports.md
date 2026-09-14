# ADR-0003: Canonical Execution Request/Result and Shared Transport Boundary

- **Status:** Accepted
- **Date:** 2026-08-12
- **Decision owner:** L9 architecture
- **Law:** `PEER_EXECUTION_THIN_ADAPTER_LAW.yaml`

## Context

Provider-specific drivers currently assemble prompts, pass permissions, choose process arguments, enforce timeouts, parse host output, and map Program results. These concerns mix canonical execution semantics with provider syntax.

## Decision

Peer Execution Core will expose two provider-neutral boundary contracts:

### `CanonicalExecutionRequest`

Carries at minimum:

- execution and task identity;
- Program Lock and rendered-contract digests;
- worktree reference;
- objective;
- context-manifest reference;
- permission-profile reference;
- inference budget;
- timeout budget;
- requested capabilities;
- telemetry context.

### `CanonicalProviderResult`

Carries at minimum:

- execution identity;
- status;
- structured payload;
- raw-output digest;
- provider metadata;
- usage metadata when observable;
- session/run identity when observable;
- observed capabilities;
- normalized errors;
- transport evidence references.

Provider-specific data remains inside `provider_metadata`, raw evidence, or provider extensions. It MUST NOT alter canonical Program, change-IR, verification, or convergence semantics.

Transport implementations are separate reusable components. Providers that share a subprocess pattern or protocol MUST share the same transport implementation. Transport owns mechanics such as process lifecycle, streaming, cancellation where supported, timeout mechanics, environment/evidence capture, and protocol errors.

Canonical Program receipts are constructed above the provider boundary from canonical results and evidence.

## Consequences

- Provider adapters collapse to mapping plus invocation binding.
- Subprocess behavior is implemented once.
- Future Anthropic-compatible, OpenAI-compatible, MCP, or other protocol families can be added as shared transports rather than per-provider rewrites.
- Usage and cost telemetry can be normalized without making Program state provider-specific.

## Rejected alternatives

### Let each provider return Program receipts

Rejected because providers are workers/evidence producers, not Program truth authorities.

### Put provider-specific request fields in canonical task contracts

Rejected because it contaminates reusable contracts and creates model lock-in.
