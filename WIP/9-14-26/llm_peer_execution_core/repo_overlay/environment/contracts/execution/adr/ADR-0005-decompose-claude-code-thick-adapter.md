# ADR-0005: Decompose Claude Code from Thick Gold Standard to Thin Provider

- **Status:** Accepted
- **Date:** 2026-08-12
- **Decision owner:** L9 architecture
- **Law:** `PEER_EXECUTION_THIN_ADAPTER_LAW.yaml`

## Context

Current `Cursor-Governance` documentation explicitly describes Claude Code as the thicker gold-standard adapter and instructs thinner adapters to catch up. The Claude Program Execution path currently owns reusable prompt construction, permission rendering, subprocess execution, output parsing, and result mapping. The Executable Peer Contract also records an exemption for Claude-owned scheduler/autonomy content.

That pattern violates the intended architecture: every peer should receive the same execution capabilities from shared upstream infrastructure, with only host/provider translation remaining local.

## Decision

Claude Code is reclassified as **Provider #1**, not the architectural gold standard.

Migration MUST extract reusable Claude behavior into Peer Execution Core or shared transports before peer expansion. The target Claude provider retains only:

- Claude executable/host availability probing;
- Claude-specific capability declaration;
- mapping from `CanonicalExecutionRequest` to Claude invocation fields/flags;
- invocation through the shared subprocess transport;
- mapping from Claude output/errors to `CanonicalProviderResult`.

The following Claude-local target patterns are deprecated and must move upstream when reusable:

- admitted-dispatch concurrency and join mechanics;
- permission policy/rendering;
- context assembly;
- inference budgets;
- generic timeout/retry/process lifecycle;
- telemetry schema;
- canonical receipt generation;
- canonical result acceptance;
- memory semantics;
- autonomy authority.

The target architecture removes the notion that Claude gets a permanent thick-adapter exemption. If a Claude-specific host feature is truly unique, it is exposed as a capability and consumed through the shared execution contract; it does not become new authority.

## Consequences

- Other peers gain Claude-discovered capabilities without copying Claude code.
- Codex, Gemini, Manus, Cursor, and future providers implement only thin translation/invocation surfaces.
- Existing Claude-specific code is a migration source, not a template to clone.
- Current repository behavior may remain temporarily nonconformant during an explicit migration campaign, but no new thick peer adapter may be added.

## Rejected alternatives

### Preserve the Claude exception indefinitely

Rejected because it institutionalizes unequal peer capabilities and duplication.

### Copy Claude into each adapter and refactor later

Rejected because duplication becomes the migration burden and multiplies defects.
