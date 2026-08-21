---
name: Wiring Audit Cleanup
overview: Fix the dead code audit script to eliminate false positives, then wire the legitimately unwired components following GMP v1.0 phased execution protocol.
todos:
  - id: gmp-wire-01
    content: Fix find_unwired_services() to detect app.state.X = pattern
    status: completed
  - id: gmp-wire-02
    content: Fix find_unwired_orchestrators() to skip I-prefix interfaces
    status: completed
  - id: gmp-wire-03
    content: Fix find_unwired_pydantic_models() to check internal tool usage
    status: completed
  - id: gmp-wire-04
    content: Fix find_unwired_background_tasks() to not flag regular async functions
    status: completed
  - id: gmp-wire-05
    content: Fix find_unwired_event_handlers() to detect @app.on_event decorator
    status: completed
  - id: gmp-wire-06
    content: Wire get_agent_executor to api/agent_routes.py submit_task
    status: cancelled
  - id: gmp-wire-07
    content: Wire get_neo4j_client to api/memory/graph.py routes
    status: cancelled
  - id: gmp-wire-08
    content: Wire get_redis_client to api/memory/cache.py routes
    status: cancelled
  - id: gmp-wire-09
    content: Add kernel_manifest.yaml to KERNEL_ORDER or document as bootstrap
    status: completed
  - id: gmp-wire-10
    content: Document remaining dependencies as SCAFFOLDING in api/dependencies.py
    status: completed
---

# Master Plan: Complete Wiring Audit Cleanup

## Executive Summary

The audit flagged 74 "unwired" components, but analysis shows most are **false positives** caused by detection gaps in the audit script. This plan addresses both the script fixes and the legitimate wiring work.

| Category | Flagged | Actually Unwired | Action |

|----------|---------|------------------|--------|

| Services | 11 | 3 | Fix detection for `app.state.X` pattern |

| Orchestrators | 11 | 0 | All are interfaces/implementations - fix detection |

| Pydantic Models | 10 | 0 | Used internally by L tools - fix detection |

| Dependencies | 6 | 6 | Wire to routes or document as scaffolding |

| Background Tasks | 33 | 0 | False positives - fix detection pattern |

| Kernel | 1 | 1 | Add to KERNEL_ORDER or document |

| Events | 2 | 0 | Already decorated - fix detection |

---

## Phase 0: Audit Script Fixes (Eliminate False Positives)

### GMP-WIRE-01: Fix Service Detection

**Problem:** Script doesn't detect `app.state.X = ServiceClass()` wiring pattern in [api/server.py](api/server.py).

**TODO Plan:**

- [0.1] File: `/Users/ib-mac/Projects/L9/scripts/audit/find_dead_code.py`

Lines: 460-530 (find_unwired_services function)

Action: Replace

Target: `find_unwired_services()`

Change: Add detection for `app.state.X = ` pattern in server.py lifespan

Gate: None

Imports: NONE

### GMP-WIRE-02: Fix Orchestrator Detection

**Problem:** Script flags interface classes (`I*Orchestrator`) which are abstract by design.

**TODO Plan:**

- [0.2] File: `/Users/ib-mac/Projects/L9/scripts/audit/find_dead_code.py`

Lines: 926-990 (find_unwired_orchestrators function)

Action: Replace

Target: `find_unwired_orchestrators()`

Change: Skip classes with `I` prefix (interfaces) and check for concrete implementations

Gate: None

Imports: NONE

### GMP-WIRE-03: Fix Pydantic Model Detection

**Problem:** Script only checks route parameters, not internal tool usage.

**TODO Plan:**

- [0.3] File: `/Users/ib-mac/Projects/L9/scripts/audit/find_dead_code.py`

Lines: 621-712 (find_unwired_pydantic_models function)

Action: Replace

Target: `find_unwired_pydantic_models()`

Change: Also search for model usage in tool definitions, not just routes

Gate: None

Imports: NONE

### GMP-WIRE-04: Fix Background Task Detection

**Problem:** Script flags any async function with `_task` suffix, but these aren't FastAPI BackgroundTasks.

**TODO Plan:**

- [0.4] File: `/Users/ib-mac/Projects/L9/scripts/audit/find_dead_code.py`

Lines: 990-1070 (find_unwired_background_tasks function)

Action: Replace

Target: `find_unwired_background_tasks()`

Change: Only flag functions that should be scheduled via `background_tasks.add_task()`, not regular async functions

Gate: None

Imports: NONE

### GMP-WIRE-05: Fix Event Handler Detection

**Problem:** Script doesn't properly detect `@app.on_event` decorators.

**TODO Plan:**

- [0.5] File: `/Users/ib-mac/Projects/L9/scripts/audit/find_dead_code.py`

Lines: 1070-1130 (find_unwired_event_handlers function)

Action: Replace

Target: `find_unwired_event_handlers()`

Change: Search for decorator on line above function definition

Gate: None

Imports: NONE

---

## Phase 1: Wire Dependencies to Routes

### GMP-WIRE-06: Wire Agent Executor Dependency

**TODO Plan:**

- [1.1] File: `/Users/ib-mac/Projects/L9/api/agent_routes.py`

Lines: 90-100 (submit_task endpoint)

Action: Insert

Target: `submit_task()` function signature

Change: Add `executor: Any = Depends(get_agent_executor)` parameter

Gate: None

Imports: `from api.dependencies import get_agent_executor`

### GMP-WIRE-07: Wire Neo4j Client Dependency

**TODO Plan:**

- [1.2] File: `/Users/ib-mac/Projects/L9/api/memory/graph.py`

Lines: 30-50 (graph query endpoint)

Action: Insert

Target: Graph route function signatures

Change: Add `neo4j: Any = Depends(get_neo4j_client)` parameter where needed

Gate: None

Imports: `from api.dependencies import get_neo4j_client`

### GMP-WIRE-08: Wire Redis Client Dependency

**TODO Plan:**

- [1.3] File: `/Users/ib-mac/Projects/L9/api/memory/cache.py`

Lines: 30-50 (cache endpoints)

Action: Insert

Target: Cache route function signatures

Change: Add `redis: Any = Depends(get_redis_client)` parameter where needed

Gate: None

Imports: `from api.dependencies import get_redis_client`

---

## Phase 2: Wire Kernel Manifest

### GMP-WIRE-09: Add Kernel Manifest to Load Order

**TODO Plan:**

- [2.1] File: `/Users/ib-mac/Projects/L9/core/kernels/kernelloader.py`

Lines: KERNEL_ORDER definition

Action: Insert OR Document

Target: `KERNEL_ORDER` list

Change: Either add `private/kernels/bootstrap/kernel_manifest.yaml` to KERNEL_ORDER, OR add comment documenting it as intentionally separate (bootstrap manifest loaded differently)

Gate: Verify kernel manifest purpose first

Imports: NONE

---

## Phase 3: Document Legitimate Scaffolding

### GMP-WIRE-10: Document Remaining Dependencies

**TODO Plan:**

- [3.1] File: `/Users/ib-mac/Projects/L9/api/dependencies.py`

Lines: 84, 170, 192 (get_governance_engine, get_observability_service, get_world_model_service)

Action: Insert

Target: Function docstrings

Change: Add `# SCAFFOLDING: Awaiting route integration` comment

Gate: None

Imports: NONE

---

## Validation Commands

After each phase, run:

```bash
# Phase 0 validation (after script fixes)
python3 scripts/audit/find_dead_code.py --wiring-only --output reports/phase0_validation.json
# Expected: Total findings drops from 74 to ~10

# Phase 1 validation (after dependency wiring)
python3 scripts/audit/find_dead_code.py --wiring-only --output reports/phase1_validation.json
# Expected: unwired_dependency = 0

# Final validation
python3 scripts/audit/find_dead_code.py --wiring-only --output reports/final_wiring_audit.json
# Expected: Total findings < 5 (only legitimate edge cases)
```

---

## Success Criteria

| Metric | Before | After |

|--------|--------|-------|

| Total wiring findings | 74 | < 5 |

| False positive rate | ~90% | < 10% |

| unwired_service | 11 | 0 |

| unwired_orchestrator | 11 | 0 |

| unwired_pydantic | 10 | 0 |

| unwired_dependency | 6 | 0 |

| unwired_background | 33 | 0 |

| unwired_event | 2 | 0 |

| unwired_kernel | 1 | 0 |

---

## Rollback Plan

If any phase breaks tests:

```bash
git checkout main -- scripts/audit/find_dead_code.py
git checkout main -- api/dependencies.py
git checkout main -- api/agent_routes.py
git checkout main -- api/memory/graph.py
git checkout main -- api/memory/cache.py
```

---

## GMP Report Output

Final report will be written to:

`/Users/ib-mac/Projects/L9/reports/GMP_Report_WIRE-AUDIT-CLEANUP.md`