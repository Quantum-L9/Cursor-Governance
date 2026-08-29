---
name: Memory RLS + TTL Fix
overview: Wire RLS session scope calls and TTL eviction SQL procedures into the memory substrate layer. 6 files, ~120 lines of surgical additions, no rewrites.
todos:
  - id: rls-repo
    content: Add set_session_scope() and call_maintenance_procedure() to SubstrateRepository
    status: pending
  - id: rls-service
    content: Wire RLS session scope calls in MemorySubstrateService before queries
    status: pending
  - id: tenant-fields
    content: Add tenant_id, org_id, user_id, role fields to MemoryRequest
    status: pending
  - id: orchestrator-context
    content: Pass tenant context from MemoryOrchestrator to substrate service
    status: pending
  - id: housekeeping-sql
    content: Wire orchestrators/memory/housekeeping.py to SQL procedures
    status: pending
  - id: engine-sql
    content: Wire memory/housekeeping.py HousekeepingEngine to SQL CALL
    status: pending
---

# Memory Misalignment Fix: RLS + TTL Wiring

## Problem Statement

Migration 0008 provides multi-tenant RLS and TTL eviction via SQL procedures, but the Python layer never calls them:
- `l9_set_scope()` - never invoked before queries
- `evict_expired_packets()` / `decay_unaccessed_importance()` / `refresh_memory_views()` - never called by housekeeping
- `MemoryRequest` lacks tenant fields (`tenant_id`, `org_id`, `user_id`, `role`)

## Corrected File Paths

Your TODO plan referenced incorrect paths. Actual paths:

| Plan Path | Actual Path |
|-----------|-------------|
| `orchestrators/memory_substrate_service.py` | [`memory/substrate_service.py`](memory/substrate_service.py) |
| `orchestrators/memory_orchestrator.py` | [`orchestrators/memory/orchestrator.py`](orchestrators/memory/orchestrator.py) |
| `orchestrators/memory_housekeeping.py` | [`orchestrators/memory/housekeeping.py`](orchestrators/memory/housekeeping.py) |
| `orchestrators/memory_interface.py` | [`orchestrators/memory/interface.py`](orchestrators/memory/interface.py) |
| `memory/substrate_repository.py` | [`memory/substrate_repository.py`](memory/substrate_repository.py) (correct) |
| `memory/housekeeping.py` | [`memory/housekeeping.py`](memory/housekeeping.py) (exists, full engine) |

## Architecture Note

There are TWO housekeeping files:
1. [`orchestrators/memory/housekeeping.py`](orchestrators/memory/housekeeping.py) - Thin wrapper (calls `delete_packets_before`, `vacuum_analyze`)
2. [`memory/housekeeping.py`](memory/housekeeping.py) - Full engine (`HousekeepingEngine` with TTL eviction via raw SQL)

The full engine does manual `DELETE FROM packet_store WHERE ttl < NOW()` but migration 0008 provides `CALL evict_expired_packets()` which logs eviction counts. We should wire to the SQL procedures.

---

## Edit Plan: 6 Files, ~21 Edits

### FILE 1: [`memory/substrate_repository.py`](memory/substrate_repository.py)

Add RLS session scope method at repository layer.

| Edit | Location | Action | Details |
|------|----------|--------|---------|
| 1.1 | After `health_check()` (~line 740) | INSERT | New method `set_session_scope()` to execute `SELECT l9_set_scope(...)` |
| 1.2 | After 1.1 | INSERT | New method `call_maintenance_procedure()` to execute `CALL <procedure>()` |

### FILE 2: [`memory/substrate_service.py`](memory/substrate_service.py)

Add RLS session scope calls before queries.

| Edit | Location | Action | Details |
|------|----------|--------|---------|
| 2.1 | After `__init__` (~line 75) | INSERT | New method `set_session_scope()` that delegates to repository |
| 2.2 | In `write_packet()` (~line 103) | WRAP | Call `await self._repository.set_session_scope()` before DAG run |
| 2.3 | In `query_packets()` (~line 220) | WRAP | Call scope setter before queries |
| 2.4 | In `trigger_world_model_update()` (~line 480) | WRAP | Call scope setter before world model call |
| 2.5 | In `semantic_search()` (~line 290) | WRAP | Call scope setter before search |

### FILE 3: [`orchestrators/memory/interface.py`](orchestrators/memory/interface.py)

Extend `MemoryRequest` with tenant fields.

| Edit | Location | Action | Details |
|------|----------|--------|---------|
| 3.1 | In `MemoryRequest` class (~line 25) | INSERT | Add fields: `tenant_id`, `org_id`, `user_id`, `role` with defaults |

### FILE 4: [`orchestrators/memory/orchestrator.py`](orchestrators/memory/orchestrator.py)

Pass tenant context to substrate service.

| Edit | Location | Action | Details |
|------|----------|--------|---------|
| 4.1 | In `_batch_write()` (~line 107) | INSERT | Call `substrate.set_session_scope(request.tenant_id, ...)` before storing |
| 4.2 | In `_replay()` (~line 128) | INSERT | Call scope setter before queries |
| 4.3 | In `_garbage_collect()` (~line 164) | INSERT | Pass tenant context to housekeeping |

### FILE 5: [`orchestrators/memory/housekeeping.py`](orchestrators/memory/housekeeping.py)

Wire TTL eviction to SQL procedures.

| Edit | Location | Action | Details |
|------|----------|--------|---------|
| 5.1 | After `compact()` (~line 155) | INSERT | New method `run_scheduled_maintenance()` calling all 4 SQL procedures |
| 5.2 | In `garbage_collect()` (~line 93) | INSERT | Call `_evict_expired_packets()` after age-based GC |
| 5.3 | After 5.1 | INSERT | Add methods: `_call_evict_expired_packets()`, `_call_decay_importance()`, `_call_refresh_views()` |

### FILE 6: [`memory/housekeeping.py`](memory/housekeeping.py)

Wire `HousekeepingEngine.evict_expired_ttl()` to SQL procedure instead of raw DELETE.

| Edit | Location | Action | Details |
|------|----------|--------|---------|
| 6.1 | In `evict_expired_ttl()` (~line 155) | REPLACE | Change raw DELETE to `CALL evict_expired_packets()` |
| 6.2 | After `gc_unused_tags()` (~line 365) | INSERT | New method `run_scheduled_maintenance()` calling all 4 procedures |

---

## Summary Table

| File | Edits | LOC Added | Risk |
|------|-------|-----------|------|
| `memory/substrate_repository.py` | 2 | ~25 | LOW |
| `memory/substrate_service.py` | 5 | ~35 | LOW |
| `orchestrators/memory/interface.py` | 1 | ~8 | VERY LOW |
| `orchestrators/memory/orchestrator.py` | 3 | ~15 | LOW |
| `orchestrators/memory/housekeeping.py` | 3 | ~40 | LOW |
| `memory/housekeeping.py` | 2 | ~20 | LOW |
| **TOTAL** | **16** | **~143** | **LOW** |

---

## No-Touch Constraints

- Migration files (0001-0009) - SQL is source of truth
- `plasticos_memory_substrate` domain tables
- `buyer_profiles`, `supplier_profiles`, `transactions`
- `websocket_orchestrator.py`, `kernel_loader.py`

---

## Validation Checklist (Post-Execution)

- [ ] `l9_set_scope()` called before every substrate write/query
- [ ] `evict_expired_packets()` called via SQL CALL, not raw DELETE
- [ ] `MemoryRequest` includes `tenant_id`, `org_id`, `user_id`, `role`
- [ ] `run_scheduled_maintenance()` callable from housekeeping
- [ ] No out-of-scope files touched
- [ ] All edits are INSERT/WRAP, no rewrites
