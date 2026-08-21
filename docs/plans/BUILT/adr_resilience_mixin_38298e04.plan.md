---
name: ADR Resilience Mixin
overview: Create ADR-0014 documenting the Protocol + Mixin pattern for adding resilience (CircuitBreaker + DeadLetterQueue + Retry) to L9 components using Dependency Inversion Principle.
todos:
  - id: create-adr
    content: Create readme/adr/0014-resilience-mixin-pattern.md with full ADR content
    status: completed
  - id: update-catalog
    content: Add ADR-0014 entry to readme/repo-index/adr_catalog.txt
    status: completed
---

# ADR-0014: Resilience Mixin Pattern

## Context

L9 has resilience infrastructure (`CircuitBreaker`, `DeadLetterQueue`, `RetryPolicy`) but only `SubstrateDagOrchestrator` uses all three. Six other components need the same pattern. Using DIP via Protocol + Mixin reduces boilerplate from ~40 lines to ~5 lines per component.

## Scope

**Tier:** UX (documentation only)

**Files to Create:**

- `readme/adr/0014-resilience-mixin-pattern.md` — New ADR

**Files to Modify:**

- `readme/repo-index/adr_catalog.txt` — Add entry for ADR-0014

## ADR Content Structure

The ADR will document:

1. **Status:** Proposed
2. **Pattern:** Protocol defines contract; Mixin provides `with_resilience()` method
3. **Files:** Where to create the implementation (future work)
4. **Architecture Diagram:** Show DIP relationship
5. **Protocol Definition:** `ResilientService` protocol
6. **Mixin Implementation:** `ResilienceMixin` class with `with_resilience()`
7. **Usage Pattern:** How components inherit and use
8. **Components to Apply:** List of 6 components
9. **AI Guidance:** DO/DO NOT rules

## Key Code Snippets to Document

### Protocol (contract)

```python
class ResilientService(Protocol):
    _circuit_breaker: Optional[CircuitBreaker]
    _dlq: Optional[DeadLetterQueue]
    _retry_policy: Optional[RetryPolicy]
```

### Mixin (implementation)

```python
class ResilienceMixin:
    async def with_resilience(self, operation, envelope, name: str):
        # CB check → retry loop → DLQ on exhaustion
```

### Usage

```python
class IngestionPipeline(ResilienceMixin):
    async def ingest(self, envelope):
        return await self.with_resilience(
            operation=lambda: self._do_ingest(envelope),
            envelope=envelope,
            operation_name="ingest"
        )
```

## References

- Extends [ADR-0009: Circuit Breaker Resilience](readme/adr/0009-circuit-breaker-resilience.md)
- Uses [ADR-0002: TYPE_CHECKING Pattern](readme/adr/0002-circular-import-prevention.md) for imports
- Aligns with SOLID principles (DIP specifically)