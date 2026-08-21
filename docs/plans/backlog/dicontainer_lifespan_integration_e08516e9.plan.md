---
name: DIContainer Lifespan Integration
overview: Integrate the DIContainer + ExecutorComposer pattern from `examples/fastapi_lifespan_di_bootstrap.py` into the production `api/server.py` lifespan, replacing manual service instantiation with proper dependency injection while preserving all existing functionality.
todos:
  - id: di-bootstrap
    content: Add DIContainer bootstrap after singleton auto-registration in api/server.py lifespan (~line 605)
    status: pending
  - id: executor-composer
    content: Replace manual AgentExecutorService creation (lines 1087-1280) with ExecutorComposer pattern
    status: pending
  - id: shutdown-cleanup
    content: Add DIContainer cleanup in lifespan finally block
    status: pending
  - id: delete-example
    content: Delete examples/fastapi_lifespan_di_bootstrap.py after adoption
    status: pending
  - id: verify
    content: Verify server startup, /health, /lchat endpoints work correctly
    status: pending
isProject: false
---

# DIContainer + ExecutorComposer Integration into api/server.py

## Current State

The production `api/server.py` lifespan (lines 477-2600+) manually instantiates services:

```python
# Current pattern (lines 1087-1262)
aios_runtime = create_aios_runtime()
tool_registry = create_executor_tool_registry(...)
executor = AgentExecutorService(
    aios_runtime=aios_runtime,
    tool_registry=tool_registry,
    substrate_service=app.state.substrate_service,
    ...
)
app.state.agent_executor = executor
```

## Target State

Use DIContainer + ExecutorComposer pattern from the example:

```python
# Target pattern
from core.di.container import DIContainer
from core.di.bootstrap import bootstrap_di_container
from core.agents.executor_composer import ExecutorComposer

container = DIContainer()
bootstrap_di_container(container)  # Registers all services

composer = ExecutorComposer()
composer.set_di_container(container)
executor = composer.compose()  # Resolves deps automatically

app.state.di_container = container
app.state.agent_executor = executor
```

## Key Files

- [api/server.py](api/server.py) - Production lifespan to modify (lines 477-1500)
- [core/di/container.py](core/di/container.py) - DIContainer class (exists, working)
- [core/di/bootstrap.py](core/di/bootstrap.py) - bootstrap_di_container() (exists, working)
- [core/agents/executor_composer.py](core/agents/executor_composer.py) - ExecutorComposer (exists, working)
- [examples/fastapi_lifespan_di_bootstrap.py](examples/fastapi_lifespan_di_bootstrap.py) - Reference pattern (to be deleted after adoption)

## Integration Strategy

**Preserve** all existing functionality:

- Environment validation (lines 496-515)
- ModuleRegistry initialization (lines 525-572)
- Singleton auto-registration (lines 574-604)
- Memory service initialization via `init_service()` (lines 840-880)
- Tool embeddings sync (lines 1128-1147)
- Session startup checks (lines 1150-1200)
- All Stage 2/3 service wiring (lines 1800-2600)

**Replace** manual AgentExecutorService creation (lines 1087-1280) with:

1. DIContainer bootstrap early in lifespan
2. ExecutorComposer.compose() to create executor
3. Store container in app.state for debugging endpoints

## Changes Required

### 1. Add DIContainer bootstrap after singleton auto-registration (~line 605)

```python
# NEW: Bootstrap DIContainer (DI/DIP pattern)
from core.di.container import DIContainer
from core.di.bootstrap import bootstrap_di_container

_di_container = DIContainer()
bootstrap_stats = bootstrap_di_container(_di_container)
app.state.di_container = _di_container
logger.info("DIContainer bootstrapped", **bootstrap_stats)
```

### 2. Replace manual executor creation (lines 1087-1280) with ExecutorComposer

```python
# REPLACE manual instantiation with:
from core.agents.executor_composer import ExecutorComposer

composer = ExecutorComposer()
composer.set_di_container(_di_container)
executor = composer.compose()
app.state.agent_executor = executor
```

### 3. Add shutdown cleanup (~line 2650 in finally block)

```python
# Cleanup DIContainer on shutdown
if hasattr(app.state, 'di_container') and app.state.di_container:
    app.state.di_container.clear_all()
    logger.info("DIContainer cleared")
```

### 4. Delete examples file after adoption

Remove `examples/fastapi_lifespan_di_bootstrap.py` - pattern now in production.

## Risk Assessment

- **Tier**: RUNTIME_TIER (lifespan/bootstrap code)
- **Risk**: MEDIUM - changes initialization order but preserves all functionality
- **Rollback**: Revert single file (`api/server.py`)
- **Testing**: Existing tests + manual server startup verification

## Verification

1. Server starts without errors
2. `/health` returns healthy status
3. `/lchat` endpoint works (AgentExecutorService functional)
4. All existing app.state services remain available
5. DIContainer debug endpoints work (optional: add `/di/services` route)
