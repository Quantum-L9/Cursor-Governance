---
name: Clean DI Guard Pattern
overview: Replace NotImplementedError with a proper dependency injection guard pattern using RuntimeError with descriptive messages, following FastAPI best practices and L9 contract compliance.
todos:
  - id: di-1
    content: Create DependencyNotConfiguredError in app/core/exceptions.py
    status: completed
  - id: di-2
    content: "Update score_api.py: Replace 5 NotImplementedError with DependencyNotConfiguredError"
    status: completed
  - id: di-3
    content: "Update base.py: Replace raise NotImplementedError with ellipsis in abstract method"
    status: completed
isProject: false
---

# Clean Dependency Injection Guard Pattern

## Problem Analysis

The 6 `NotImplementedError` instances fall into two categories:

### Category 1: FastAPI Dependency Stubs (5 instances in `score_api.py`)

These are placeholder functions for FastAPI's `Depends()` system. They exist to define the dependency signature but are meant to be overridden at app startup via `app.dependency_overrides`.

```python
def get_score_engine():
    """Injected by app startup."""
    raise NotImplementedError("ScoreEngine not configured")
```

**Issue:** `NotImplementedError` semantically means "subclass must implement this" (abstract method pattern). These are not abstract methods — they are configuration guards that should fail loudly if dependencies are not wired.

### Category 2: Abstract Method (1 instance in `base.py`)

```python
@abstractmethod
async def enrich(self, domain: str, payload: dict[str, Any]) -> EnrichmentResult:
    raise NotImplementedError
```

**Issue:** This is a valid use of `NotImplementedError` in an abstract method, but the `@abstractmethod` decorator already enforces implementation. The `raise NotImplementedError` is redundant — Python's ABC machinery prevents instantiation of classes with unimplemented abstract methods.

---

## Solution

### Option A: Custom Exception (Recommended)

Create a dedicated `DependencyNotConfiguredError` that:

1. Is semantically correct (configuration error, not implementation error)
2. Provides clear error messages for debugging
3. Can be caught specifically in tests
4. Complies with L9 banned pattern rules (no `NotImplementedError` outside tests)

### Option B: RuntimeError with Factory Pattern

Use `RuntimeError` directly with a factory function that provides consistent error formatting.

---

## Implementation Plan

### 1. Create Custom Exception

Add to [app/core/exceptions.py](app/core/exceptions.py) (or create if not exists):

```python
class DependencyNotConfiguredError(RuntimeError):
    """Raised when a required dependency is not configured at app startup."""

    def __init__(self, dependency_name: str, hint: str = ""):
        message = f"{dependency_name} not configured"
        if hint:
            message += f". {hint}"
        super().__init__(message)
```

### 2. Update score_api.py (5 changes)

Replace each `NotImplementedError` with `DependencyNotConfiguredError`:

```python
from ..core.exceptions import DependencyNotConfiguredError

def get_score_engine():
    """Injected by app startup via dependency_overrides."""
    raise DependencyNotConfiguredError(
        "ScoreEngine",
        "Call configure_score_dependencies() in lifespan"
    )
```

### 3. Update base.py (1 change)

Remove the redundant `raise NotImplementedError` from the abstract method — the `@abstractmethod` decorator is sufficient:

```python
@abstractmethod
async def enrich(self, domain: str, payload: dict[str, Any]) -> EnrichmentResult:
    """
    Perform enrichment for a given domain and payload.
    ...
    """
    ...  # Ellipsis is the Pythonic way to mark abstract method body
```

---

## Files to Modify


| File                                                                               | Changes                                                             |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| [app/core/exceptions.py](app/core/exceptions.py)                                   | Add `DependencyNotConfiguredError` class                            |
| [app/score/score_api.py](app/score/score_api.py)                                   | Replace 5 `NotImplementedError` with `DependencyNotConfiguredError` |
| [app/services/enrichment/sources/base.py](app/services/enrichment/sources/base.py) | Replace `raise NotImplementedError` with `...` (ellipsis)           |


---

## Benefits

1. **Semantic correctness**: `DependencyNotConfiguredError` clearly indicates a configuration issue, not a missing implementation
2. **L9 compliance**: Removes all `NotImplementedError` from production code (banned pattern)
3. **Better debugging**: Error messages include the dependency name and a hint for resolution
4. **Testability**: Custom exception can be caught specifically in integration tests
5. **Pythonic**: Uses `...` for abstract methods per PEP 3107 conventions
