---
name: Python 3.12 Cleanup
overview: Fix type hint runtime error in substrate_repository.py, clean up __import__() in dev scripts, and remove dry-run artifacts. All fixes are surgical 1-line changes.
todos:
  - id: fix-substrate-repo
    content: Add `from __future__ import annotations` to memory/substrate_repository.py
    status: pending
  - id: fix-bootstrap-refactor
    content: Replace __import__("datetime") with direct import in scripts/refactoring/bootstrap_refactor.py
    status: pending
  - id: fix-shebang
    content: Update shebang from python3.11 to python3 in scripts/agents/verify_agent_executor.py
    status: pending
  - id: cleanup-artifacts
    content: Delete .refactor-reports/ and .refactor-config/ directories
    status: pending
  - id: verify-fixes
    content: Run verify_agent_executor.py to confirm fixes work
    status: pending
---

# Python 3.12 Alignment and Cleanup Plan

## Analysis Summary

| File | Status | Issue | Fix |

|------|--------|-------|-----|

| `memory/substrate_repository.py` | BLOCKER | TypeError at runtime on line 67 | Add future annotations |

| `core/error_tracking.py` | DONE | Already fixed | None needed |

| `email_agent/triage.py` | DONE | User already cleaned up | None needed |

| `scripts/agents/verify_agent_executor.py` | MINOR | Shebang says 3.11 | Update to python3 |

| `scripts/refactoring/bootstrap_refactor.py` | LOW | `__import__()` usage | Direct import |

## Reasoning

**Abductive**: The TypeError occurs because `asyncpg.Connection` is a metaclass (`ConnectionMeta`) that doesn't implement `__or__`. When Python evaluates `ContextVar[asyncpg.Connection | None]` at runtime, it fails.

**Deductive**: Adding `from __future__ import annotations` defers all annotation evaluation to string form, avoiding runtime type operations entirely.

**Inductive**: This pattern already works in [core/error_tracking.py](core/error_tracking.py) (line 11) which uses the same approach.

**Confidence**: 95% - well-established pattern, minimal risk.

## Changes

### 1. BLOCKER: Fix substrate_repository.py

[memory/substrate_repository.py](memory/substrate_repository.py) line 8 - Add future import after docstring:

```python
"""
L9 Memory Substrate - Repository Layer
...
"""

from __future__ import annotations  # ADD THIS LINE

# ============================================================================
__dora_meta__ = {
```

This fixes the error:

```
TypeError: unsupported operand type(s) for |: 'ConnectionMeta' and 'NoneType'
```

### 2. LOW: Fix bootstrap_refactor.py

[scripts/refactoring/bootstrap_refactor.py](scripts/refactoring/bootstrap_refactor.py) - Replace `__import__("datetime")` with direct import.

Add at top (around line 19):

```python
from datetime import datetime
```

Replace line 281:

```python
# OLD: "timestamp": __import__("datetime").datetime.now().isoformat(),
# NEW: "timestamp": datetime.now().isoformat(),
```

Replace line 343:

```python
# OLD: "generated": __import__("datetime").datetime.now().isoformat(),
# NEW: "generated": datetime.now().isoformat(),
```

### 3. MINOR: Update verify_agent_executor.py shebang

[scripts/agents/verify_agent_executor.py](scripts/agents/verify_agent_executor.py) line 1:

```python
# OLD: #!/usr/bin/env python3.11
# NEW: #!/usr/bin/env python3
```

### 4. CLEANUP: Remove dry-run artifacts

Delete directories created by bootstrap_refactor.py dry run:

- `.refactor-reports/` (2 files)
- `.refactor-config/` (4 files)

## Execution Order

```
1. substrate_repository.py  (unblocks agent executor)
     |
2. bootstrap_refactor.py   (parallel - no dependency)
     |
3. verify_agent_executor.py (parallel - no dependency)
     |
4. Delete .refactor-* dirs  (cleanup)
     |
5. Verify: python3 scripts/agents/verify_agent_executor.py
```

## Token Efficiency

- Total edits: 5 surgical changes
- No file rewrites
- No new files created
- Estimated: ~20 lines touched across 3 files
