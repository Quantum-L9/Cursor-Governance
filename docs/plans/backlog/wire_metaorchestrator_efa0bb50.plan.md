---
name: Wire MetaOrchestrator
overview: Wire MetaOrchestrator and BlueprintAdapter into server.py lifespan, create api/routes/meta.py router with endpoints for blueprint evaluation, comparison, and improvement suggestions, and register the router with the FastAPI app.
todos:
  - id: meta-1
    content: Add AsyncOpenAI, MetaOrchestrator, BlueprintAdapter imports to server.py
    status: pending
  - id: meta-2
    content: Add MetaOrchestrator instantiation block in lifespan() after agent executor
    status: pending
    dependencies:
      - meta-1
  - id: meta-3
    content: Create api/routes/meta.py with dependency injection and 4 endpoints
    status: pending
    dependencies:
      - meta-1
  - id: meta-4
    content: Register meta_router in server.py with prefix /meta
    status: pending
    dependencies:
      - meta-3
  - id: meta-5
    content: Update api/routes/__init__.py docstring to include meta.py
    status: pending
    dependencies:
      - meta-3
  - id: meta-6
    content: Update docs/ROADMAP.md - move MetaOrchestrator to Completed section
    status: pending
    dependencies:
      - meta-4
  - id: meta-7
    content: Run import validation test to confirm wiring is correct
    status: pending
    dependencies:
      - meta-4
---

# Wire MetaOrchestrator into L9 API

## Architecture Overview

```mermaid
flowchart TD
    subgraph Startup [Lifespan Startup]
        AsyncOpenAI[AsyncOpenAI Client]
        BlueprintAdapter[BlueprintAdapter]
        MetaOrchestrator[MetaOrchestrator]

        AsyncOpenAI --> BlueprintAdapter
        BlueprintAdapter --> MetaOrchestrator
        MetaOrchestrator --> AppState[app.state.meta_orchestrator]
    end

    subgraph Routes [/meta/* Endpoints]
        EvaluateRoute[POST /meta/evaluate]
        CompareRoute[POST /meta/compare]
        ImproveRoute[POST /meta/improve]
    end

    AppState --> Routes
```

## Files to Modify

| File | Action | Purpose |
|------|--------|---------|
| [api/server.py](api/server.py) | Modify | Add imports, instantiation, and router registration |
| [api/routes/meta.py](api/routes/meta.py) | Create | New router with 4 endpoints |
| [api/routes/__init__.py](api/routes/__init__.py) | Modify | Add meta.py to docstring |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Modify | Update status from "NOT WIRED" to "WIRED" |

## Implementation Details

### 1. server.py Changes

**Add imports (after line 152):**
```python
from openai import AsyncOpenAI
from orchestrators.meta.orchestrator import MetaOrchestrator
from orchestrators.meta.adapter import BlueprintAdapter
```

**Add instantiation in lifespan() (after line 416, after agent executor init):**
```python
# Initialize MetaOrchestrator (LLM-powered blueprint evaluation)
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    try:
        logger.info("Initializing MetaOrchestrator...")
        async_openai = AsyncOpenAI(api_key=openai_api_key)
        blueprint_adapter = BlueprintAdapter(
            openai_client=async_openai,
            model=os.getenv("META_ORCHESTRATOR_MODEL", "gpt-4"),
        )
        meta_orchestrator = MetaOrchestrator(adapter=blueprint_adapter)
        app.state.meta_orchestrator = meta_orchestrator
        logger.info("MetaOrchestrator initialized")
    except Exception as e:
        logger.error(f"Failed to initialize MetaOrchestrator: {e}", exc_info=True)
        app.state.meta_orchestrator = None
else:
    logger.warning("MetaOrchestrator not initialized: OPENAI_API_KEY required")
    app.state.meta_orchestrator = None
```

**Add router registration (after line 856, after factory_router):**
```python
# Meta Orchestrator router (blueprint evaluation)
from api.routes.meta import router as meta_router
app.include_router(meta_router, prefix="/meta")
```

### 2. api/routes/meta.py (New File)

Router with 4 endpoints:
- `GET /meta/test` - Health check
- `POST /meta/evaluate` - Evaluate N blueprints, select best
- `POST /meta/compare` - Compare A vs B head-to-head
- `POST /meta/improve` - Suggest improvements for a blueprint

Dependency injection pattern same as reasoning.py.

### 3. ROADMAP.md Update

Move MetaOrchestrator from "Backlog" to "Completed" section with wiring details.

## Validation Checks

After implementation, verify with:
```python
LOCAL_DEV=true python -c "
from api.routes.meta import router
from orchestrators.meta.orchestrator import MetaOrchestrator
from orchestrators.meta.adapter import BlueprintAdapter
from openai import AsyncOpenAI
print('Imports OK')
"
```
