---
name: Memory RLS+TTL v1.1
overview: Wire RLS session scope and TTL eviction SQL procedures into memory substrate layer. 5 files, 14 surgical edits, ~260 LOC. Includes Phase 0A verification gates and proper execution sequencing.
todos:
  - id: phase-0a
    content: Verify migration 0008 SQL procedures exist (l9_set_scope, evict_expired_*)
    status: completed
  - id: edit-1.1
    content: Add tenant_id/org_id/user_id/role fields to MemoryRequest
    status: completed
    dependencies:
      - phase-0a
  - id: edit-2.1
    content: Add set_session_scope() method to MemorySubstrateService
    status: completed
    dependencies:
      - phase-0a
  - id: edit-2.2-2.4
    content: Wrap write_packet/query_packets/trigger_world_model with RLS scope
    status: completed
    dependencies:
      - edit-2.1
  - id: edit-3.1-3.4
    content: Pass RLS context through MemoryOrchestrator execute/_batch_write/_replay/_gc
    status: completed
    dependencies:
      - edit-1.1
      - edit-2.1
  - id: edit-4.1-4.4
    content: Wire Housekeeping to SQL procedures + add run_scheduled_maintenance()
    status: completed
    dependencies:
      - edit-3.1-3.4
  - id: edit-5.1
    content: Create RLS configuration documentation with deployment checklist
    status: completed
    dependencies:
      - edit-4.1-4.4
---

# Memory Misalignment Fix v1.1: RLS + TTL Wiring

## Critical Fixes from v1.0

| Issue | Severity | Fix Applied |

|-------|----------|-------------|

| Missing RLS Fields on MemoryRequest | CRITICAL | Interface extended BEFORE orchestrator uses it |

| Undefined set_session_scope() Signature | CRITICAL | Full method signature with tenant/org/user/role params |

| Missing SQL Procedure Verification | HIGH | Phase 0A blocking checks added |

| Connection Pool Reset Undefined | MEDIUM | Documentation + checklist added |

| No Error Handling for RLS Failures | MEDIUM | Try/catch blocks with RuntimeError |---

## Phase 0A: Blocking Verification (Execute First)

Before any code edits, verify migration 0008 procedures exist:

```sql
SELECT proname FROM pg_proc WHERE proname IN (
    'l9_set_scope',
    'evict_expired_packets',
    'decay_unaccessed_importance',
    'refresh_memory_views',
    'evict_expired_reflections'
);
-- Expected: 5 rows. If fewer: STOP, migration 0008 not applied.
```

---

## Execution Sequence (14 Edits, 5 Files)

### Phase 1: Interface Extension (Prerequisite)

**Edit 1.1** - [`orchestrators/memory/interface.py`](orchestrators/memory/interface.py)Location: In `MemoryRequest` class, after `gc_threshold_days` field (~line 31)Action: INSERT 4 new fields

```python
# Multi-tenant RLS context (required for all operations)
tenant_id: str = Field(..., description="Tenant UUID for RLS isolation")
org_id: str = Field(..., description="Organization UUID for RLS isolation")
user_id: str = Field(..., description="User UUID for RLS isolation")
role: str = Field(default="end_user", description="User role: platform_admin, tenant_admin, org_admin, end_user")
```

---

### Phase 2: Substrate Service RLS Integration

**Edit 2.1** - [`memory/substrate_service.py`](memory/substrate_service.py)Location: After `__init__()` (~line 75)Action: INSERT new method `set_session_scope()`

```python
async def set_session_scope(
    self,
    tenant_id: str,
    org_id: str,
    user_id: str,
    role: str = "end_user"
) -> None:
    """Set PostgreSQL session variables for RLS."""
    try:
        async with self._repository.acquire() as conn:
            await conn.execute(
                """SELECT l9_set_scope($1::uuid, $2::uuid, $3::uuid, $4::text)""",
                tenant_id, org_id, user_id, role,
            )
        logger.debug(f"RLS session scope set", tenant_id=tenant_id, role=role)
    except Exception as e:
        logger.error(f"Failed to set RLS session scope: {e}", exc_info=True)
        raise RuntimeError(f"RLS scope initialization failed: {e}") from e
```

**Edit 2.2** - `write_packet()` signature + scope call**Edit 2.3** - `query_packets()` signature + scope call**Edit 2.4** - `trigger_world_model_update()` signature + scope call---

### Phase 3: Orchestrator Integration

**Edit 3.1** - [`orchestrators/memory/orchestrator.py`](orchestrators/memory/orchestrator.py)Location: In `execute()`, update `_batch_write()` call to pass request**Edit 3.2** - Update `_batch_write()` to accept request context and call `substrate.set_session_scope()`**Edit 3.3** - Update `_replay()` to set RLS scope before queries**Edit 3.4** - Update `_garbage_collect()` signature from `threshold_days: int` to `request: MemoryRequest`---

### Phase 4: Housekeeping TTL Integration

**Edit 4.1** - [`orchestrators/memory/housekeeping.py`](orchestrators/memory/housekeeping.py)Location: `garbage_collect()` method signatureAction: Add RLS context parameters + scope setting with error handling**Edit 4.2** - In `garbage_collect()`, after age-based GC, add TTL eviction call**Edit 4.3** - INSERT new method `_evict_expired_packets()` calling SQL procedure

```python
async def _evict_expired_packets(self) -> int:
    """Evict packets via CALL evict_expired_packets() from migration 0008."""
    repository = await self._get_repository()
    if repository is None:
        return 0
    try:
        async with repository._pool.acquire() as conn:
            await conn.execute("CALL evict_expired_packets()")
        logger.debug("TTL eviction procedure executed")
        return 0  # Exact count in database logs
    except Exception as e:
        logger.error(f"TTL eviction failed: {e}")
        return 0
```

**Edit 4.4** - INSERT new method `run_scheduled_maintenance()` calling all 4 procedures:

- `CALL decay_unaccessed_importance(30, 0.1)`
- `CALL refresh_memory_views()`
- `CALL evict_expired_packets()`
- `CALL evict_expired_reflections()`

---

### Phase 5: Configuration Documentation

**Edit 5.1** - Create or update RLS configuration documentationDocument connection pool behavior, session scope isolation requirements, and deployment checklist.---

## Summary Table

| Edit | File | Type | LOC | Risk |

|------|------|------|-----|------|

| 1.1 | `orchestrators/memory/interface.py` | INSERT | 4 | VERY LOW |

| 2.1 | `memory/substrate_service.py` | INSERT | 25 | LOW |

| 2.2 | `memory/substrate_service.py` | WRAP | 5 | LOW |

| 2.3 | `memory/substrate_service.py` | WRAP | 5 | LOW |

| 2.4 | `memory/substrate_service.py` | WRAP | 5 | LOW |

| 3.1 | `orchestrators/memory/orchestrator.py` | WRAP | 2 | VERY LOW |

| 3.2 | `orchestrators/memory/orchestrator.py` | WRAP | 8 | LOW |

| 3.3 | `orchestrators/memory/orchestrator.py` | WRAP | 10 | LOW |

| 3.4 | `orchestrators/memory/orchestrator.py` | WRAP | 6 | LOW |

| 4.1 | `orchestrators/memory/housekeeping.py` | WRAP | 15 | MEDIUM |

| 4.2 | `orchestrators/memory/housekeeping.py` | INSERT | 14 | MEDIUM |

| 4.3 | `orchestrators/memory/housekeeping.py` | INSERT | 35 | LOW |

| 4.4 | `orchestrators/memory/housekeeping.py` | INSERT | 85 | LOW |

| 5.1 | `docs/MEMORY_RLS_SETUP.md` | INSERT | 40 | VERY LOW |

| **TOTAL** | **5 Files** | **Surgical** | **~260** | **LOW** |---

## No-Touch Constraints

- Migration files (0001-0009) - SQL is source of truth
- `plasticos_memory_substrate` domain tables
- `buyer_profiles`, `supplier_profiles`, `transactions`
- `websocket_orchestrator.py`, `kernel_loader.py`
- `memory/housekeeping.py` (HousekeepingEngine) - separate from orchestrator housekeeping

---

## Validation Checklist (Post-Execution)

- [ ] Phase 0A: All 5 SQL procedures exist in database
- [ ] `MemoryRequest` includes `tenant_id`, `org_id`, `user_id`, `role`
- [ ] `set_session_scope()` called before every substrate write/query
- [ ] `evict_expired_packets()` called via SQL CALL, not raw DELETE
- [ ] `run_scheduled_maintenance()` callable from housekeeping
- [ ] Error handling catches RLS failures with RuntimeError
- [ ] All edits are INSERT/WRAP, no file rewrites
- [ ] Cross-tenant access test: DENIED without admin role
- [ ] Admin override test: ALLOWED with platform_admin role

---

## Status: LOCKED FOR PHASE 1 EXECUTION
