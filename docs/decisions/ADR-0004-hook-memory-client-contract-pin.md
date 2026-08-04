# ADR-0004: The hook memory client is a contract-pinned stdlib mirror of `memory.*`

## Status

Accepted

## Date

2026-08-04

## Context

ADR-0003 keeps two memory entry points and requires them to share one contract.
The only real divergence between them was the **client implementation**: the hook
path uses a hand-rolled, stdlib-only JSON-RPC client
(`environment/claude-code/memory/memory_client.py`), while the model uses the real
`l9-shared-memory` MCP server. Two implementations reading one contract, with
nothing pinning them together, is exactly how the audit's RC1 arose: the hook read
`records`/`hits` from a `memory.hydrate` result whose contract key is `sections`
(`HydrationResult`), so every prefetch counted zero and injected nothing — and no
test or validator caught it (MEM-005), because the validators only checked file
presence and wiring parity, never the live response shape.

We want to keep the stdlib client (its zero-dependency portability is a feature,
per ADR-0003) **and** guarantee it cannot drift from the server contract again.

## Decision

1. **Centralize the contract in the client.** `memory_client.py` owns the only
   reads of the `memory.*` response keys, exposed as accessors:
   - `hydrated_sections(bundle)` → the `sections` list from a `memory.hydrate`
     result (never `records`/`hits`).
   - `search_hits(bundle)` → the `hits` list from a `memory.search` result.
   - `render_sections(bundle, max_chars=…)` → budget-bounded plain text for
     SessionStart context injection.
   Hook consumers (`memory_prefetch.py`, and any future consumer) MUST use these
   accessors instead of re-reading raw keys.

2. **Pin the contract with an executed, network-free test.**
   `environment/claude-code/tests/test_memory_client_contract.py` asserts the
   accessors against fixtures that are shape-faithful to the server's
   `ContextSection`/`HydrationResult`/search contracts, and explicitly guards the
   RC1 drift (a hydrate result has no `records`/`hits`; search and hydrate do not
   share a content key).

3. **Enforce the pin, don't merely ship it.** `validate_memory_enforcement.py`
   executes the contract test as part of its run. A present-but-unrun test is what
   let RC1 pass — presence is not proof. The test is network-free so CI without
   memory stays green.

## Consequences

- Reintroducing `bundle.get("records")`/`bundle.get("hits")` on a hydrate result,
  or otherwise diverging the stdlib client from the `memory.*` contract, fails
  `validate_memory_enforcement.py` instead of silently zeroing memory in
  production.
- The stdlib client stays dependency-free and portable (ADR-0003 alternative
  preserved); parity with the MCP path is achieved by shared *contract*, not shared
  *runtime*.
- If the server contract changes (e.g. new `HydrationResult` fields), the fixtures
  in the contract test are the one place to update, and the failure is localized.

## Alternatives considered

- **Import the real MCP client SDK into the hooks.** Rejected: adds a runtime
  dependency to enforcement code that must run in any consumer repo without a venv.
- **Trust code review to keep the client aligned.** Rejected: RC1 shipped through
  review and two passing validators precisely because nothing exercised the live
  contract shape.

## References

- ADR-0002 — memory enforcement contract
- ADR-0003 — memory architecture: two entry points, one contract
- MEM-001/002 (RC1), MEM-005 in
  `reports/graphiti-memory-audit-2026-08-04/CLAUDE_MEMORY_DEFECT_REGISTER.yaml`
- `environment/claude-code/memory/memory_client.py`,
  `hooks/memory_prefetch.py`,
  `tests/test_memory_client_contract.py`,
  `validate_memory_enforcement.py`
