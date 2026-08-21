---
name: Wiring Integrity Checks
overview: Expand `find_dead_code.py` with comprehensive wiring integrity detection for FastAPI routers, L9 tools/kernels/agents, Pydantic models, dependency injection, and event handlers. Prioritized by confidence level and L9-specific patterns.
todos:
  - id: tier1-tools
    content: Implement find_unwired_tools() - detect TOOL_DEFINITIONS not registered in ToolGraph
    status: completed
  - id: tier1-pydantic
    content: Implement find_unwired_pydantic_models() - detect BaseModel subclasses never used in routes
    status: completed
  - id: tier1-deps
    content: Implement find_unwired_dependencies() - detect Depends() provider functions never injected
    status: completed
  - id: tier2-kernels
    content: Implement find_unwired_kernels() - detect YAML kernels not in KERNEL_ORDER
    status: completed
  - id: tier2-agents
    content: Implement find_unwired_agents() and find_unwired_orchestrators()
    status: completed
  - id: tier3-events
    content: Implement find_unwired_event_handlers() and find_unwired_background_tasks()
    status: completed
  - id: tier3-middleware
    content: Implement find_unwired_middleware() and find_unwired_websocket_routes()
    status: completed
  - id: cli-enhance
    content: Add --wiring-only flag and confidence tier grouping to CLI output
    status: completed
---

# Wiring Integrity Checks for find_dead_code.py

## Current State

Already implemented in [scripts/audit/find_dead_code.py](scripts/audit/find_dead_code.py):

- `find_unwired_routers()` - APIRouter definitions not mounted
- `find_unwired_services()` - *Service/*Executor/*Pipeline classes not instantiated

## Proposed Additions (14 New Checks)

### Tier 1: HIGH Priority (High confidence, high impact)

#### 1. `find_unwired_tools()` - L9 Tool Registry

Detects tool definitions not registered in ToolGraph.

**Pattern to detect:**

```python
# Defined in core/tools/*.py
TOOL_DEFINITIONS = [{"name": "foo", ...}]
L9_TOOLS = [ToolDefinition(...)]

# But never: await ToolGraph.register_tool(tool)
```

**Files to scan:** `core/tools/*.py`

**Confidence:** 85%

---

#### 2. `find_unwired_pydantic_models()` - Unused Request/Response Models

Detects Pydantic models defined but never used in route signatures.

**Pattern to detect:**

```python
# Defined
class UserCreateRequest(BaseModel): ...
class UserResponse(BaseModel): ...

# But never used in:
# - Route parameter: def endpoint(request: UserCreateRequest)
# - Response model: @router.post(..., response_model=UserResponse)
```

**Files to scan:** `api/**/*.py`, `core/schemas/*.py`

**Confidence:** 80%

---

#### 3. `find_unwired_dependencies()` - Orphaned FastAPI Dependencies

Detects `Depends()` provider functions never injected.

**Pattern to detect:**

```python
# Defined in api/dependencies.py
def get_db_session(): ...
def get_current_user(): ...

# But never: Depends(get_db_session)
```

**Files to scan:** `api/dependencies.py` definitions vs all `Depends()` usages

**Confidence:** 85%

---

### Tier 2: MEDIUM Priority (L9-specific, moderate confidence)

#### 4. `find_unwired_kernels()` - YAML Kernels Not in Load Order

Detects kernel YAML files not listed in `KERNEL_ORDER`.

**Pattern to detect:**

```python
# File exists: private/kernels/00_system/11_new_kernel.yaml
# But not in KERNEL_ORDER list in kernelloader.py
```

**Files to scan:** `private/kernels/**/*.yaml` vs `core/kernels/kernelloader.py`

**Confidence:** 95% (very deterministic)

---

#### 5. `find_unwired_kernel_wiring()` - Kernel Wiring Modules Not Imported

Detects kernel wiring modules in `core/kernel_wiring/` not imported.

**Pattern to detect:**

```python
# File: core/kernel_wiring/safety_wiring.py exists
# But never imported in kernel bootstrap sequence
```

**Files to scan:** `core/kernel_wiring/*.py`

**Confidence:** 75%

---

#### 6. `find_unwired_agents()` - Agent Configs Never Referenced

Detects agent YAML configs never loaded by AgentRegistry.

**Pattern to detect:**

```yaml
# config/agents/research-agent-v1.yaml exists
# But never: AgentRegistry.load("research-agent-v1")
```

**Files to scan:** `config/agents/*.yaml`

**Confidence:** 70%

---

#### 7. `find_unwired_orchestrators()` - Orchestrator Classes Orphaned

Detects orchestrator interfaces never instantiated.

**Pattern to detect:**

```python
# orchestrators/*/interface.py defines class
# But never instantiated or type-hinted in routes
```

**Files to scan:** `orchestrators/*/interface.py`

**Confidence:** 70%

---

### Tier 3: LOWER Priority (More complex patterns)

#### 8. `find_unwired_event_handlers()` - Startup/Shutdown Handlers

Detects `@app.on_event("startup")` style handlers not in main app.

**Pattern to detect:**

```python
# Defined somewhere
async def startup_handler(): ...

# But not: app.on_event("startup")(startup_handler)
```

**Confidence:** 65%

---

#### 9. `find_unwired_background_tasks()` - Async Tasks Never Scheduled

Detects functions designed for `BackgroundTasks` never added.

**Pattern to detect:**

```python
# Function signature suggests background task
async def process_webhook_async(data: dict): ...

# But never: background_tasks.add_task(process_webhook_async)
```

**Confidence:** 60%

---

#### 10. `find_unwired_middleware()` - Middleware Not Applied

Detects middleware classes/functions never added to app.

**Pattern to detect:**

```python
# Defined
class RateLimitMiddleware: ...

# But never: app.add_middleware(RateLimitMiddleware)
```

**Confidence:** 70%

---

#### 11. `find_unwired_websocket_routes()` - WebSocket Handlers Orphaned

Detects `@router.websocket()` handlers in files not mounted.

**Files to scan:** All files with `@router.websocket` decorator

**Confidence:** 75%

---

#### 12. `find_unwired_settings()` - Settings Classes Never Loaded

Detects Settings/Config classes never instantiated.

**Pattern to detect:**

```python
# config/settings.py
class DatabaseSettings(BaseSettings): ...

# But never: settings = DatabaseSettings()
```

**Confidence:** 65%

---

#### 13. `find_unwired_schema_registry()` - Schemas Not Registered

Detects schemas defined but not in `SchemaRegistry`.

**Pattern to detect:**

```python
# core/schemas/schema_registry.py has SCHEMA_REGISTRY dict
# Schema class exists but not in registry
```

**Confidence:** 80%

---

#### 14. `find_orphaned_test_fixtures()` - Fixtures Never Used

Detects pytest fixtures in conftest.py never referenced.

**Pattern to detect:**

```python
# conftest.py
@pytest.fixture
def mock_db(): ...

# But never: def test_foo(mock_db): ...
```

**Confidence:** 75%

---

## Implementation Structure

```python
# New symbol types to add
WIRING_SYMBOL_TYPES = [
    "unwired_router",      # existing
    "unwired_service",     # existing
    "unwired_tool",        # NEW
    "unwired_pydantic",    # NEW
    "unwired_dependency",  # NEW
    "unwired_kernel",      # NEW
    "unwired_agent",       # NEW
    "unwired_orchestrator",# NEW
    "unwired_event",       # NEW
    "unwired_middleware",  # NEW
    "unwired_websocket",   # NEW
    "unwired_settings",    # NEW
    "unwired_schema",      # NEW
    "orphaned_fixture",    # NEW
]
```

## CLI Enhancement

Add `--wiring-only` flag to run only wiring checks:

```bash
python scripts/audit/find_dead_code.py --wiring-only
```

## Confidence Tiers in Output

Group findings by confidence tier:

- HIGH (80-100%): Almost certainly unwired
- MEDIUM (65-79%): Likely unwired, verify manually
- LOW (50-64%): Possible issue, may be false positive
