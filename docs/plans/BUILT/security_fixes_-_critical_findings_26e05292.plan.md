---
name: Security Fixes - Critical Findings
overview: "Fix 5 critical security findings: unauthenticated agent endpoints, unauthenticated WebSocket, RLS session scope enforcement, memory tool registration bug, and non-transactional ingestion. Includes comprehensive test coverage for regression protection."
todos:
  - id: auth-agent-endpoints
    content: Add authentication to /agent/task and /agent/execute endpoints using Depends(verify_api_key)
    status: completed
  - id: auth-websocket
    content: Add WebSocket authentication to /ws/agent and /lws endpoints - validate token before accept()
    status: completed
  - id: fix-memory-tool-bug
    content: Fix memory tool registration bug - change app.state.memory_service to app.state.substrate_service
    status: completed
  - id: fix-rls-scope
    content: Fix RLS session scope propagation - use single connection/transaction for all operations
    status: completed
  - id: transactional-ingestion
    content: Wrap core ingestion writes (packet_store, memory_events) in transaction for atomicity
    status: completed
  - id: test-coverage
    content: Add comprehensive test coverage for all security fixes - auth tests, RLS isolation tests, transaction tests
    status: completed
---

# Security Fixes - Critical Findings Remediation Plan

## Executive Summary

This plan addresses 5 critical security findings identified in the security audit:

1. **Unauthenticated agent execution endpoints** (Critical) - `/agent/task` and `/agent/execute`
2. **Unauthenticated WebSocket control plane** (Critical) - `/ws/agent` and `/lws`
3. **RLS session scope not enforced** (High) - Connection pool scope isolation
4. **Memory tool registration bug** (Medium) - Wrong app state key
5. **Non-transactional ingestion** (High) - Partial write failures

**Impact:** These vulnerabilities enable unauthenticated remote code execution, agent impersonation, cross-tenant data access, and data integrity issues.

**Approach:** Fix in priority order (Critical → High → Medium), with comprehensive test coverage for each fix.

---

## Architecture Context

### Current Authentication Pattern

- `api/auth.py` provides `verify_api_key()` using `L9_EXECUTOR_API_KEY`
- Used in: `api/routes/commands.py`, `api/vps_executor.py`, `api/server.py` (`/lchat`)
- Pattern: `_: bool = Depends(verify_api_key)`

### WebSocket Authentication Pattern

- FastAPI WebSocket endpoints cannot use `Depends()` directly
- Must validate auth token during handshake before `accept()`
- Token can be passed via query params or first message

### RLS Session Scope Pattern

- PostgreSQL session variables set via `l9_set_scope()` function
- Variables are connection-scoped (lost when connection released)
- Current: `set_session_scope()` uses separate connection, then releases
- Required: Single connection/transaction spanning all operations

### Transaction Pattern

- asyncpg supports transactions via `async with conn.transaction():`
- Current: Multiple independent writes with separate try/except
- Required: Wrap core writes in single transaction

---

## Detailed Implementation Plan

### TODO 1: Add Authentication to Agent Endpoints (CRITICAL)

**Files to Modify:**

- `api/agent_routes.py` (lines 87, 124)

**Changes:**

1. Import `verify_api_key` from `api.auth`
2. Add `Depends(verify_api_key)` to `/agent/task` endpoint
3. Add `Depends(verify_api_key)` to `/agent/execute` endpoint
4. Update docstrings to document auth requirement

**Code Changes:**

```python
# Add import at top
from api.auth import verify_api_key
from fastapi import Depends

# Modify /agent/task endpoint (line 87)
@router.post("/task")
async def submit_task(
    payload: dict,
    _: bool = Depends(verify_api_key)  # Add auth dependency
):

# Modify /agent/execute endpoint (line 124)
@router.post("/execute", response_model=ExecuteTaskResponse)
async def execute_task(
    request: Request,
    body: ExecuteTaskRequest,
    _: bool = Depends(verify_api_key)  # Add auth dependency
) -> ExecuteTaskResponse:
```

**Test Changes:**

- `tests/docker/test_stack_smoke.py`: Update `test_agent_execute_basic()` and `test_agent_task_submit()` to require auth
- Add new tests: `test_agent_execute_unauthorized()`, `test_agent_task_unauthorized()`

**Validation:**

- Verify 401 response without auth header
- Verify 200 response with valid `Authorization: Bearer {L9_EXECUTOR_API_KEY}`

---

### TODO 2: Add WebSocket Authentication (CRITICAL)

**Files to Modify:**

- `api/server.py` (lines 2456-2541, 2549-2640)
- `runtime/websocket_orchestrator.py` (lines 46-67)
- `core/schemas/event_stream.py` (add auth_token field to AgentHandshake)

**Changes:**

1. Create `verify_websocket_auth()` helper function
2. Modify `/ws/agent` to validate token before `accept()`
3. Modify `/lws` to validate token before `accept()`
4. Update `AgentHandshake` schema to include optional `auth_token`
5. Update orchestrator to validate agent_id binding to token

**Code Changes:**

**New helper in `api/server.py`:**

```python
async def verify_websocket_auth(websocket: WebSocket, token: Optional[str] = None) -> bool:
    """Verify WebSocket authentication token."""
    from api.auth import EXECUTOR_API_KEY

    if not EXECUTOR_API_KEY:
        return False

    # Token can come from query params or first message
    if not token:
        query_token = websocket.query_params.get("token")
        if query_token:
            token = query_token

    if not token or token != EXECUTOR_API_KEY:
        return False

    return True
```

**Modify `/ws/agent` endpoint:**

```python
@app.websocket("/ws/agent")
async def agent_ws_endpoint(websocket: WebSocket) -> None:
    # Validate auth BEFORE accept
    token = websocket.query_params.get("token")
    if not await verify_websocket_auth(websocket, token):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await websocket.accept()

    # Validate token in handshake message too
    try:
        raw = await websocket.receive_json()
        handshake = AgentHandshake.model_validate(raw)

        # Verify agent_id binding (if token provided in handshake)
        if handshake.auth_token and handshake.auth_token != token:
            await websocket.close(code=1008, reason="Invalid auth token")
            return

        agent_id = handshake.agent_id
        # ... rest of handler
```

**Modify `/lws` endpoint:**

```python
@app.websocket("/lws")
async def l_ws(websocket: WebSocket) -> None:
    # Validate auth BEFORE accept
    token = websocket.query_params.get("token")
    if not await verify_websocket_auth(websocket, token):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await websocket.accept()
    # ... rest of handler
```

**Update `core/schemas/event_stream.py`:**

```python
class AgentHandshake(BaseModel):
    agent_id: str
    agent_version: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    hostname: Optional[str] = None
    platform: Optional[str] = None
    auth_token: Optional[str] = None  # Add this field
```

**Test Changes:**

- Add `test_websocket_agent_unauthorized()` - verify connection rejected without token
- Add `test_websocket_lws_unauthorized()` - verify connection rejected without token
- Update existing WebSocket tests to include auth token

---

### TODO 3: Fix RLS Session Scope Propagation (HIGH)

**Files to Modify:**

- `memory/substrate_service.py` (lines 107-152, 158-249)
- `memory/substrate_repository.py` (add transaction context manager)
- `memory/ingestion.py` (update to use scoped connection)

**Changes:**

1. Add `transaction()` context manager to `SubstrateRepository`
2. Modify `write_packet()` to accept optional connection parameter
3. Modify `set_session_scope()` to return connection or use transaction
4. Update DAG operations to use same connection/transaction

**Code Changes:**

**Add to `memory/substrate_repository.py`:**

```python
@asynccontextmanager
async def transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
    """Acquire a connection and start a transaction with RLS scope."""
    async with self.acquire() as conn:
        async with conn.transaction():
            yield conn
```

**Modify `memory/substrate_service.py` - `set_session_scope()`:**

```python
async def set_session_scope(
    self,
    tenant_id: str,
    org_id: str,
    user_id: str,
    role: str = "end_user",
) -> asyncpg.Connection:
    """
    Set PostgreSQL session variables for RLS and return connection.

    Returns connection that must be used for all subsequent operations.
    """
    conn = await self._repository._pool.acquire()
    try:
        await conn.execute(
            """SELECT l9_set_scope($1::uuid, $2::uuid, $3::uuid, $4::text)""",
            tenant_id, org_id, user_id, role,
        )
        return conn
    except Exception as e:
        await self._repository._pool.release(conn)
        raise RuntimeError(f"RLS scope initialization failed: {e}") from e
```

**Modify `memory/substrate_service.py` - `write_packet()`:**

```python
async def write_packet(
    self,
    packet_in: PacketEnvelopeIn,
    tenant_id: Optional[str] = None,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None,
    connection: Optional[asyncpg.Connection] = None,  # Add this
) -> PacketWriteResult:
    """
    Write packet with optional RLS-scoped connection.

    If connection provided, uses it for all operations (maintains RLS scope).
    Otherwise, uses default pool (no RLS scope).
    """
    # If RLS scope required but no connection provided, set it
    if (tenant_id and org_id and user_id) and not connection:
        connection = await self.set_session_scope(tenant_id, org_id, user_id)
        try:
            # Run DAG with scoped connection
            result = await self._dag.run_with_connection(envelope, connection)
        finally:
            await self._repository._pool.release(connection)
    else:
        # Normal flow without RLS
        result = await self._dag.run(envelope)
```

**Alternative Approach (Simpler):**

Use `SET LOCAL` within transaction to scope RLS variables:

```python
async def write_packet_with_rls(
    self,
    packet_in: PacketEnvelopeIn,
    tenant_id: str,
    org_id: str,
    user_id: str,
    role: str = "end_user",
) -> PacketWriteResult:
    """Write packet with RLS scope using transaction-local variables."""
    async with self._repository.transaction() as conn:
        # Set RLS scope within transaction (SET LOCAL)
        await conn.execute(
            """SELECT l9_set_scope($1::uuid, $2::uuid, $3::uuid, $4::text)""",
            tenant_id, org_id, user_id, role,
        )

        # All DAG operations use same connection
        envelope = packet_in.to_envelope()
        result = await self._dag.run_with_connection(envelope, conn)

        return result
```

**Test Changes:**

- Add `test_rls_scope_isolation()` - verify tenant A cannot read tenant B data
- Add `test_rls_scope_persists_in_transaction()` - verify scope maintained across operations
- Add `test_rls_scope_lost_after_transaction()` - verify scope cleared after transaction

---

### TODO 4: Fix Memory Tool Registration Bug (MEDIUM)

**Files to Modify:**

- `api/server.py` (line 1239)

**Changes:**

1. Change `app.state.memory_service` to `app.state.substrate_service`

**Code Changes:**

```python
# Line 1239 - Change from:
substrate_service = getattr(app.state, "memory_service", None)

# To:
substrate_service = getattr(app.state, "substrate_service", None)
```

**Test Changes:**

- Add `test_memory_tools_registered()` - verify tools registered when substrate available
- Verify tools are accessible after registration

**Validation:**

- Check server startup logs for "Memory tools registered" message
- Verify memory tools appear in tool registry

---

### TODO 5: Wrap Ingestion in Transaction (HIGH)

**Files to Modify:**

- `memory/ingestion.py` (lines 96-215)
- `memory/substrate_repository.py` (add transaction support)

**Changes:**

1. Wrap core writes (packet_store, memory_events) in transaction
2. Keep embedding, artifacts, lineage, graph sync as best-effort (outside transaction)
3. Implement idempotent cleanup for partial failures

**Code Changes:**

**Modify `memory/ingestion.py` - `ingest()` method:**

```python
async def ingest(
    self,
    packet_in: PacketEnvelopeIn,
    embed: Optional[bool] = None,
    generate_tags: Optional[bool] = None,
) -> PacketWriteResult:
    """Ingest packet with transactional core writes."""
    # ... validation code ...

    envelope = packet_in.to_envelope()

    # Core writes in transaction (atomic)
    written_tables = []
    errors = []

    async with self._repository.transaction() as conn:
        try:
            # Store structured packet
            await self._store_packet_with_connection(envelope, conn)
            written_tables.append("packet_store")

            # Store memory event
            await self._store_memory_event_with_connection(envelope, conn)
            written_tables.append("agent_memory_events")

            # Transaction commits here (or rolls back on exception)
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            errors.append(f"transaction: {str(e)}")
            raise  # Transaction auto-rolls back

    # Best-effort writes (outside transaction)
    if should_embed and self._semantic_service:
        try:
            embedded = await self._embed_content(envelope)
            if embedded:
                written_tables.append("semantic_memory")
        except Exception as e:
            logger.warning(f"Embedding failed (non-critical): {e}")

    # ... rest of best-effort writes ...

    status = "ok" if not errors else "partial" if written_tables else "error"
    return PacketWriteResult(...)
```

**Add connection-aware methods to `memory/ingestion.py`:**

```python
async def _store_packet_with_connection(
    self, envelope: PacketEnvelope, conn: asyncpg.Connection
) -> None:
    """Store packet using provided connection."""
    await self._repository.insert_packet_with_connection(envelope, conn)

async def _store_memory_event_with_connection(
    self, envelope: PacketEnvelope, conn: asyncpg.Connection
) -> None:
    """Store memory event using provided connection."""
    await self._repository.insert_memory_event_with_connection(
        agent_id=envelope.metadata.agent if envelope.metadata else "default",
        event_type=envelope.packet_type,
        content=envelope.payload,
        packet_id=envelope.packet_id,
        timestamp=envelope.timestamp,
        connection=conn,
    )
```

**Add to `memory/substrate_repository.py`:**

```python
async def insert_packet_with_connection(
    self, envelope: PacketEnvelope, conn: asyncpg.Connection
) -> UUID:
    """Insert packet using provided connection (for transactions)."""
    # Same logic as insert_packet, but use provided conn instead of acquire()
    await conn.execute(...)

async def insert_memory_event_with_connection(
    self,
    agent_id: str,
    event_type: str,
    content: dict,
    packet_id: UUID,
    timestamp: datetime,
    connection: asyncpg.Connection,
) -> None:
    """Insert memory event using provided connection."""
    await connection.execute(...)
```

**Test Changes:**

- Add `test_ingestion_transaction_rollback()` - verify partial failure rolls back
- Add `test_ingestion_atomic_core_writes()` - verify packet_store + memory_events atomic
- Add `test_ingestion_best_effort_writes()` - verify embedding/lineage failures don't block

---

### TODO 6: Add Comprehensive Test Coverage (MEDIUM)

**Files to Create/Modify:**

- `tests/api/test_agent_auth.py` (new file)
- `tests/api/test_websocket_auth.py` (new file)
- `tests/memory/test_rls_isolation.py` (new file)
- `tests/memory/test_ingestion_transaction.py` (new file)
- `tests/docker/test_stack_smoke.py` (update existing tests)

**Test Structure:**

**`tests/api/test_agent_auth.py`:**

```python
def test_agent_execute_requires_auth(api_client):
    """Verify /agent/execute requires authentication."""
    response = api_client.post("/agent/execute", json={...})
    assert response.status_code == 401

def test_agent_execute_with_valid_auth(api_client):
    """Verify /agent/execute works with valid auth."""
    headers = {"Authorization": f"Bearer {os.getenv('L9_EXECUTOR_API_KEY')}"}
    response = api_client.post("/agent/execute", json={...}, headers=headers)
    assert response.status_code in [200, 503]  # 503 if executor not ready

def test_agent_task_requires_auth(api_client):
    """Verify /agent/task requires authentication."""
    response = api_client.post("/agent/task", json={...})
    assert response.status_code == 401
```

**`tests/api/test_websocket_auth.py`:**

```python
async def test_websocket_agent_rejects_unauthorized(websocket_client):
    """Verify /ws/agent rejects connection without token."""
    with pytest.raises(WebSocketDisconnect):
        async with websocket_client.connect("/ws/agent"):
            pass

async def test_websocket_lws_rejects_unauthorized(websocket_client):
    """Verify /lws rejects connection without token."""
    with pytest.raises(WebSocketDisconnect):
        async with websocket_client.connect("/lws"):
            pass
```

**`tests/memory/test_rls_isolation.py`:**

```python
async def test_rls_tenant_isolation(substrate_service):
    """Verify tenant A cannot read tenant B data."""
    # Write packet as tenant A
    await substrate_service.write_packet_with_rls(
        packet_in, tenant_id="tenant-a", org_id="org-a", user_id="user-a"
    )

    # Try to read as tenant B (should return empty)
    results = await substrate_service.search_packets_by_type(
        packet_type="test", tenant_id="tenant-b", org_id="org-b", user_id="user-b"
    )
    assert len(results) == 0
```

**`tests/memory/test_ingestion_transaction.py`:**

```python
async def test_ingestion_rollback_on_failure(ingestion_pipeline):
    """Verify transaction rolls back on core write failure."""
    # Mock repository to fail on second write
    # Verify first write also rolled back
```

---

## Implementation Order

1. **TODO 1** - Agent endpoint auth (Critical, simplest)
2. **TODO 2** - WebSocket auth (Critical, moderate complexity)
3. **TODO 4** - Memory tool bug (Medium, 1-line fix, quick win)
4. **TODO 3** - RLS scope (High, most complex, requires careful testing)
5. **TODO 5** - Transactional ingestion (High, depends on TODO 3 transaction support)
6. **TODO 6** - Test coverage (Parallel with all above)

---

## Risk Assessment

| TODO | Risk Level | Mitigation |

|------|------------|------------|

| TODO 1 | Low | Simple dependency injection, well-tested pattern |

| TODO 2 | Medium | WebSocket auth is less common, needs careful testing |

| TODO 3 | High | Complex connection management, requires thorough testing |

| TODO 4 | Low | Single line change, low risk |

| TODO 5 | Medium | Transaction logic must be correct, test thoroughly |

| TODO 6 | Low | Test-only changes, no production risk |

---

## Validation Checklist

After each TODO:

- [ ] Code changes implemented
- [ ] Tests written and passing
- [ ] Manual testing completed
- [ ] No regressions in existing functionality
- [ ] Documentation updated (if needed)

Final validation:

- [ ] All 5 security findings fixed
- [ ] All tests passing
- [ ] Security audit re-run confirms fixes
- [ ] No new vulnerabilities introduced

---

## Dependencies

- `api/auth.py` - Must exist and be functional
- `L9_EXECUTOR_API_KEY` - Must be set in environment
- PostgreSQL RLS functions - Must exist (`l9_set_scope`, etc.)
- asyncpg transaction support - Already available

---

## Estimated Effort

- TODO 1: 1 hour (code) + 1 hour (tests) = 2 hours
- TODO 2: 3 hours (code) + 2 hours (tests) = 5 hours
- TODO 3: 4 hours (code) + 3 hours (tests) = 7 hours
- TODO 4: 5 minutes (code) + 30 minutes (tests) = 35 minutes
- TODO 5: 3 hours (code) + 2 hours (tests) = 5 hours
- TODO 6: 2 hours (parallel with above)

**Total: ~21 hours** (can be parallelized where dependencies allow)
