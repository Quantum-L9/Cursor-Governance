# ADR-0001: Peer Execution Core Is Upstream of All Adapters

- **Status:** Accepted
- **Date:** 2026-08-12
- **Decision owner:** L9 architecture
- **Law:** `PEER_EXECUTION_THIN_ADAPTER_LAW.yaml`

## Context

`Quantum-L9/Cursor-Governance` currently concentrates reusable execution behavior in provider-specific paths, especially Claude Code. The current Claude driver builds prompts, resolves permissions, executes subprocesses, parses results, and maps terminal output. Other providers are represented by separate Program Execution adapters, creating pressure to copy the Claude path for every new peer.

The repository already contains shared lifecycle primitives such as capability receipts, lifecycle receipts, runtime storage, routing, and subprocess evidence. The architecture should finish that abstraction instead of making each provider reproduce it.

## Decision

Create one canonical **Peer Execution Core** upstream of every peer and provider adapter.

Peer Execution Core owns reusable execution behavior including:

- canonical request construction;
- context manifests;
- permission resolution;
- capability receipt lifecycle and freshness;
- budget, timeout, retry, and concurrency policy;
- shared transport selection;
- telemetry normalization;
- canonical result normalization;
- canonical receipt creation;
- autonomy gateway integration;
- readiness and lifecycle orchestration.

Provider and surface adapters MUST remain thin and MUST bind to this core.

The Program Controller remains above Peer Execution Core and retains Program state, readiness/advancement authority, Program Lock, leases, result admission, verification admission, and convergence.

## Consequences

- Adding a new LLM no longer means building a new execution subsystem.
- Claude Code ceases to be the architecture template and becomes one provider implementation.
- Shared behavior extracted from Claude becomes available to Cursor, Codex, Gemini, Manus, and future peers automatically.
- Peer-specific copies of scheduler, permission, context, budget, telemetry, receipt, timeout, retry, and process-runner logic become conformance defects.
- Migration is required in `Cursor-Governance`; this ADR does not claim that the current repository already conforms.

## Rejected alternatives

### Keep Claude as the thick gold standard

Rejected because it makes every new peer inherit Claude-specific implementation shape and creates recurring duplication.

### Build one thick adapter per provider

Rejected because provider proliferation would multiply lifecycle, policy, telemetry, validation, and security drift.

### Put Program state in Peer Execution Core

Rejected because it would create a second Program authority below the Controller.
