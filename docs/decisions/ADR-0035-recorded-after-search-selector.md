# ADR-0035: `recorded_after` is a search selector that skips the relevance drop

## Status

Accepted

## Date

2026-09-19

## Context

`l9-graphite-memory` already has `recorded_before` (transaction-time ceiling,
defaults to now). SessionStart's 24h agent-lane prefetch (ADR-0034) needs the
symmetric floor: return authorized records written after a timestamp, even
when the query shares no token with their content.

Without that floor, a fourth hydrate search using `Continue work in {repo}`
still drops every `write_agent` fact whose body does not overlap those words.
Tags already skip that drop; a recency window is the same kind of explicit
match. Cursor-Governance must not implement the skip by opening the store
(INV-03).

The bound pin at the time of this ADR (`l9-graphite-memory` 2.4.0) does not
expose `--recorded-after`. The consumer therefore fail-opens: it passes the
flag when present and treats an unknown-flag / refused search as "no 24h
hits," never as memory degradation.

## Decision

1. **Package.** `MemorySearchRequest.recorded_after` is a result-affecting
   selector. It is bound into `selector_identity()` and the `SearchReceipt`.
   `SEARCH_SELECTOR_CANONICALIZATION` becomes `memory.search-selectors/v2`.
   The planner returns records in the window even when `relevance<=0`, the
   same way a tag selector does. Stores filter the floor.
2. **Consumer.** `MemoryControlPlaneClient.search` may pass
   `--recorded-after`. Cursor's `SearchRequest` records the same selector.
   A receipt that does not echo it is *unbound*, not contradicted.
3. **Pin.** Cursor-Governance bumps `ops/config/memory-binding.json` to a
   release that includes this selector when that release is sealed. Until
   then the 24h prefetch is best-effort against the installed CLI.

## Consequences

- A search with `recorded_after` and no tags is a recency window, not a
  lexical query. Callers that want lexical ranking inside the window still
  get scores; they just no longer lose zero-overlap hits.
- Cross-repo fan-in is not implied. ADR-0034 keeps the 24h call on the
  primary write-namespace hint.

## Rollback

Drop `--recorded-after` from the consumer. The package field can stay: an
unused selector does not change unscoped search.
