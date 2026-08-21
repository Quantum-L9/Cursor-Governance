---
name: L9 Tool Audit Integration
overview: "Surgically integrate the high-value patterns from Phase 1-6 artifacts into L9's existing memory system. Primary focus: Add tool audit logging to ExecutorToolRegistry so every tool invocation creates an auditable memory packet."
todos:
  - id: add-memory-segment-enum
    content: Add MemorySegment enum to memory/substrate_models.py
    status: completed
  - id: create-tool-audit-helper
    content: Create memory/tool_audit.py with log_tool_invocation()
    status: completed
  - id: wire-executor-registry
    content: Wire tool audit into ExecutorToolRegistry.dispatch_tool_call()
    status: completed
  - id: add-prometheus-metrics
    content: Create telemetry/memory_metrics.py with Prometheus counters
    status: completed
  - id: validate-integration
    content: Validate tool audit packets appear in database
    status: completed
---

# L9 Tool Audit Integration Plan

## Executive Summary

L9 already has a sophisticated, working memory system (verified with round-trip test). The Phase 1-6 artifacts were designed for a different architecture. Rather than replacing L9's memory infrastructure, we will **surgically integrate the high-value patterns**:

1. **MemorySegment enum** - Standardize packet_type values
2. **Tool audit wiring** - Log every tool call to memory (PRIMARY VALUE)
3. **Prometheus metrics** - Add memory observability

## Architecture Decision

```javascript
Phase 1-6 Artifacts              L9 Integration Points
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
segments.py (MemorySegment)  →  memory/substrate_models.py (ADD enum)
tool_audit_wiring.md         →  memory/tool_audit.py (NEW helper)
                             →  core/tools/registry_adapter.py (WIRE)
telemetry.py                 →  telemetry/memory_metrics.py (NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SKIP: postgres_backend.py, neo4j_backend.py, redis_cache.py,
      substrate_service.py, bootstrap.py (L9's are working + better)
```



## Implementation Phases

### Phase 1: Add MemorySegment Enum

**File:** [memory/substrate_models.py](memory/substrate_models.py)Add `MemorySegment` enum to standardize packet_type values:

```python
class MemorySegment(str, Enum):
    """L9 memory organization - 4 canonical segments."""
    GOVERNANCE_META = "governance_meta"      # Authority, meta-prompts (immutable)
    PROJECT_HISTORY = "project_history"      # Plans, decisions, outcomes
    TOOL_AUDIT = "tool_audit"               # Tool invocation audit trail
    SESSION_CONTEXT = "session_context"      # Short-term working memory
```



### Phase 2: Create Tool Audit Helper

**File:** `memory/tool_audit.py` (NEW)Create a non-blocking helper that logs tool invocations to memory using L9's existing `ingest_packet()` pipeline:

```python
async def log_tool_invocation(
    call_id: str,
    tool_id: str,
    agent_id: str,
    task_id: str,
    status: str,
    duration_ms: int,
    error: Optional[str] = None
) -> None:
    """Log tool call to memory substrate (non-blocking)."""
```

Key design:

- Uses existing `ingest_packet()` from [memory/ingestion.py](memory/ingestion.py)
- Creates `PacketEnvelopeIn` with `packet_type="tool_audit"`
- Sets 24-hour TTL for auto-cleanup
- Catches all exceptions (never fails the tool call)

### Phase 3: Wire into ExecutorToolRegistry

**File:** [core/tools/registry_adapter.py](core/tools/registry_adapter.py)Modify `dispatch_tool_call()` to call `log_tool_invocation()` after every tool execution:

1. Import tool audit helper at top of file
2. Add timing instrumentation around tool execution
3. Call `log_tool_invocation()` in both success and error paths

The wiring pattern:

```python
# In dispatch_tool_call():
start_time = time.monotonic()
try:
    result = await executor(...)
    duration_ms = int((time.monotonic() - start_time) * 1000)
    await log_tool_invocation(..., status="success", duration_ms=duration_ms)
    return result
except Exception as e:
    duration_ms = int((time.monotonic() - start_time) * 1000)
    await log_tool_invocation(..., status="failure", error=str(e), duration_ms=duration_ms)
    raise
```



### Phase 4: Add Prometheus Memory Metrics

**File:** `telemetry/memory_metrics.py` (NEW)Add metrics inspired by Phase 1-6 `telemetry.py`:

- `l9_memory_write_total` - Counter by segment
- `l9_memory_search_total` - Counter by segment
- `l9_tool_invocation_total` - Counter by tool_id, status
- `l9_tool_duration_ms` - Histogram for latency

### Phase 5: Validate

1. Run existing memory tests to verify no regressions
2. Execute a tool call via API or test
3. Query database for `packet_type = 'tool_audit'` packets
4. Verify audit packet contains expected fields

## Files Modified

| File | Action | Lines Changed |

|------|--------|---------------|

| `memory/substrate_models.py` | ADD MemorySegment enum | +15 |

| `memory/tool_audit.py` | CREATE new file | +80 |

| `core/tools/registry_adapter.py` | WIRE audit logging | +25 |

| `telemetry/memory_metrics.py` | CREATE new file | +100 |

## What We Are NOT Doing

- NOT replacing `memory/substrate_service.py` (L9's DAG is more sophisticated)
- NOT replacing `memory/substrate_repository.py` (working Postgres backend)
- NOT replacing backend orchestration (L9's is working)
- NOT changing `bootstrap.py` (L9 already initializes correctly)
- NOT adding separate `core/memory/` folder (L9 uses `memory/`)

## Success Criteria

1. Every tool call via `ExecutorToolRegistry.dispatch_tool_call()` creates a packet in `packet_store`
2. Packets have `packet_type = "tool_audit"` and contain: call_id, tool_id, agent_id, status, duration_ms
3. Existing memory tests still pass
4. Prometheus metrics exposed at `/metrics` endpoint

## Estimated Time

- Phase 1: 5 minutes
- Phase 2: 10 minutes  
- Phase 3: 10 minutes
- Phase 4: 10 minutes
- Phase 5: 5 minutes