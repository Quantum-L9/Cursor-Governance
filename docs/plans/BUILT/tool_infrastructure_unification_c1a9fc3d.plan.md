---
name: Tool Infrastructure Unification
overview: "Wire L9's tool infrastructure for production readiness: upgrade Neo4j failure logging, set tool_graph_healthy state, replace ActionToolOrchestrator with ExecutorToolRegistry in router, add health endpoint, and document architecture."
todos:
  - id: upgrade-logging
    content: "TODO 0.1: Replace logger.debug with logger.warning at line 81 in tool_graph.py"
    status: completed
  - id: health-state
    content: "TODO 0.2: Wrap register_l_tools() with health state tracking at lines 773-779 in server.py"
    status: completed
    dependencies:
      - upgrade-logging
  - id: router-refactor
    content: "TODO 0.3: Refactor router.py - replace ActionToolOrchestrator (lines 15-18, 58-66, 83-135)"
    status: completed
    dependencies:
      - health-state
  - id: health-endpoint
    content: "TODO 0.4: Add GET /tools/health endpoint after line 135 in router.py"
    status: completed
    dependencies:
      - health-state
  - id: add-docstring
    content: "TODO 0.5: Add architecture docstring to registry_adapter.py (lines 1-15, docs only)"
    status: completed
  - id: validate
    content: "Phase 4: Run validation grep commands and test health endpoint"
    status: completed
    dependencies:
      - router-refactor
      - health-endpoint
      - add-docstring
---

# CGMP: Tool Infrastructure Unification & Startup Wiring

**Version**: 1.1 (Baseline Verified)**Status**: LOCKED FOR EXECUTION**Date**: 2026-01-04---

## Architecture Decision Summary

| Question | Decision | Rationale ||----------|----------|-----------|| Orchestrator approach | Use `app.state.tool_registry` | Matches existing singleton pattern || Health state source | `register_l_tools()` result | Neo4j is optional; registry is required |---

## PHASE 1: BASELINE VERIFICATION (COMPLETE)

### File Existence: ALL CONFIRMED

| File | Status ||------|--------|| `core/tools/tool_graph.py` | EXISTS || `core/tools/registry_adapter.py` | EXISTS || `api/server.py` | EXISTS || `api/tools/router.py` | EXISTS |

### Line Number Verification: ALL CONFIRMED

| Check | Line(s) | Verified Content ||-------|---------|------------------|| tool_graph.py logger.debug | **Line 81** | `logger.debug(f"Neo4j unavailable - skipping tool registration: {tool.name}")` || server.py register_l_tools (registry_adapter) | **Lines 773-779** | Import + call from `core.tools.registry_adapter` || router.py ActionToolOrchestrator import | **Line 18** | `from orchestrators.action_tool.orchestrator import ActionToolOrchestrator` || router.py get_action_tool_orchestrator | **Lines 58-66** | Function definition with HTTPException || router.py /execute endpoint | **Lines 83-135** | `@router.post("/execute", ...)` with orchestrator dispatch |

### Dependency Verification: ALL CONFIRMED

- `app.state.tool_registry` pattern: EXISTS (server.py line 515)
- `ExecutorToolRegistry.dispatch_tool_call()`: EXISTS (registry_adapter.py line 246)
- `app.state.tool_graph_healthy`: NOT YET SET (to be added)

---

## PHASE 2: TODO PLAN (LOCKED)

### TODO 0.1: Upgrade Neo4j Logging

**File**: [`core/tools/tool_graph.py`](core/tools/tool_graph.py)**Location**: Line 81 (inside `ToolGraph.register_tool()` method)**Action**: Replace single line with structured warning**Current** (line 81):

```python
logger.debug(f"Neo4j unavailable - skipping tool registration: {tool.name}")
```

**Target**:

```python
logger.warning(
    f"Neo4j unavailable - tool graph disabled for '{tool.name}'. "
    "Governance queries (blast radius, dependencies) unavailable.",
    extra={"alert": "neo4j_unavailable", "tool_name": tool.name}
)
```

**Note**: Metric emission OPTIONAL - only add if `core.metrics` infrastructure exists.---

### TODO 0.2: Add Health State Tracking

**File**: [`api/server.py`](api/server.py)**Location**: Lines 773-779 (L-CTO tool registration block)**Action**: Wrap `register_l_tools()` with health state tracking**Current** (lines 773-779):

```python
try:
    from core.tools.registry_adapter import register_l_tools

    tool_count = await register_l_tools()
    logger.info(f"✓ L-CTO tools registered: {tool_count} tools available")
except Exception as e:
    logger.warning(f"L-CTO tool registration skipped: {e}")
```

**Target**:

```python
try:
    from core.tools.registry_adapter import register_l_tools

    tool_count = await register_l_tools()
    if tool_count > 0:
        logger.info(f"✓ L-CTO tools registered: {tool_count} tools available")
        app.state.tool_graph_healthy = True
    else:
        logger.warning(
            "⚠️ Tool registration returned 0 tools. "
            "System will operate in degraded mode.",
            extra={"alert": "tool_graph_degraded"}
        )
        app.state.tool_graph_healthy = False
except Exception as e:
    logger.error(
        f"❌ Tool registration failed: {e}. Tool graph unavailable.",
        exc_info=True,
        extra={"alert": "tool_graph_failed"}
    )
    app.state.tool_graph_healthy = False
```

---

### TODO 0.3: Refactor Router to Use ExecutorToolRegistry

**File**: [`api/tools/router.py`](api/tools/router.py)**Action**: Replace ActionToolOrchestrator with app.state.tool_registry

#### Part A: Update imports (lines 15-18)

**Remove** (lines 15-18):

```python
from orchestrators.action_tool.interface import (
    ActionToolRequest,
)
from orchestrators.action_tool.orchestrator import ActionToolOrchestrator
```

**Replace with**:

```python
from core.tools.registry_adapter import ExecutorToolRegistry
from datetime import datetime
```



#### Part B: Replace dependency function (lines 58-66)

**Remove** (lines 58-66):

```python
def get_action_tool_orchestrator(request: Request) -> ActionToolOrchestrator:
    """Get ActionToolOrchestrator from app.state."""
    orchestrator = getattr(request.app.state, "action_tool_orchestrator", None)
    if orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="ActionToolOrchestrator not initialized. Check server logs.",
        )
    return orchestrator
```

**Replace with**:

```python
def get_tool_registry(request: Request) -> ExecutorToolRegistry:
    """
    Get ExecutorToolRegistry from app.state.
    
    DEPRECATED: ActionToolOrchestrator (v1.x) removed in v2.0.
    Using ExecutorToolRegistry for governance-aware dispatch.
    """
    registry = getattr(request.app.state, "tool_registry", None)
    if registry is None:
        raise HTTPException(
            status_code=503,
            detail="Tool registry not initialized. Check server logs.",
        )
    return registry
```



#### Part C: Update execute endpoint (lines 83-135)

**Key changes**:

1. Change dependency from `orchestrator: ActionToolOrchestrator = Depends(get_action_tool_orchestrator)` to `registry: ExecutorToolRegistry = Depends(get_tool_registry)`
2. Replace `orchestrator.execute(action_request)` with `registry.dispatch_tool_call(tool_id, arguments, context)`
3. Update docstring to note ActionToolOrchestrator deprecation
4. Adapt response mapping from ToolCallResult to ToolExecuteResponse

---

### TODO 0.4: Add Health Endpoint

**File**: [`api/tools/router.py`](api/tools/router.py)**Location**: Insert after line 135 (after execute_tool endpoint)**Action**: Add new GET endpoint**Insert**:

```python
@router.get("/health")
async def tool_graph_health(request: Request) -> dict:
    """
    Check tool graph health status.
    
    Returns:
        {
            "status": "healthy" | "degraded",
            "neo4j_available": true | false,
            "impact": null | "No blast radius/dependency queries",
            "tools_executable": true,
            "timestamp": "2026-01-04T..."
        }
    """
    is_healthy = getattr(request.app.state, "tool_graph_healthy", False)
    return {
        "status": "healthy" if is_healthy else "degraded",
        "neo4j_available": is_healthy,
        "impact": None if is_healthy else "No blast radius/dependency queries",
        "tools_executable": True,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

### TODO 0.5: Add Architecture Documentation

**File**: [`core/tools/registry_adapter.py`](core/tools/registry_adapter.py)**Location**: Lines 1-15 (replace existing docstring)**Scope**: DOCUMENTATION ONLY - no code changes**Content requirements**:

- Hybrid architecture (Neo4j governance + Postgres/registry execution)
- Graceful degradation model (Neo4j optional, registry required)
- ExecutorToolRegistry as dispatch source of truth
- ActionToolOrchestrator deprecation notice
- Usage example: `app.state.tool_registry` access pattern

---

## PHASE 3: IMPLEMENTATION ORDER

Execute in sequence (dependencies enforced):

1. TODO 0.1: tool_graph.py (line 81)
2. TODO 0.2: server.py (lines 773-779)
3. TODO 0.3: router.py (lines 15-18, 58-66, 83-135)
4. TODO 0.4: router.py (insert after line 135)
5. TODO 0.5: registry_adapter.py (lines 1-15)

---

## PHASE 4: VALIDATION CHECKLIST

| Check | Expected | Verification Command ||-------|----------|---------------------|| logger.warning in tool_graph.py line 81 | Structured alert metadata | `grep 'extra={"alert": "neo4j_unavailable"}' core/tools/tool_graph.py` || app.state.tool_graph_healthy set | Boolean state tracked | `grep "tool_graph_healthy" api/server.py` || No ActionToolOrchestrator import | Import removed | `grep "ActionToolOrchestrator" api/tools/router.py` (should return 0 matches) || ExecutorToolRegistry import present | Import added | `grep "ExecutorToolRegistry" api/tools/router.py` || Health endpoint exists | New endpoint | `grep "def tool_graph_health" api/tools/router.py` || dispatch_tool_call used | Registry dispatch | `grep "dispatch_tool_call" api/tools/router.py` |---

## PHASE 5: RECURSIVE VERIFICATION

### Protected Files (MUST NOT MODIFY)

- `websocket_orchestrator.py` - UNTOUCHED
- `docker-compose.yml` - UNTOUCHED
- `kernel_loader.py` - UNTOUCHED
- Memory substrates - UNTOUCHED

### Invariants Check

- L_INTERNAL_TOOLS list unchanged
- ToolGraph.register_tool() contract preserved
- ExecutorToolRegistry.dispatch_tool_call() contract preserved
- API response format unchanged (ToolExecuteResponse)

---

## PHASE 6: OUTPUT ARTIFACT

**Report file path**: `reports/GMP_Report_CGMP-Tools-Infrastructure.md`**Required sections**:

1. EXECUTION REPORT (task: CGMP Phase 1 Tools Infrastructure Unification)
2. TODO PLAN (all 5 TODOs with verified line numbers)
3. PHASE CHECKLIST STATUS (0-6)
4. FILES MODIFIED + LINE RANGES
5. TODO → CHANGE MAP
6. ENFORCEMENT VALIDATION RESULTS
7. PHASE 5 RECURSIVE VERIFICATION
8. FINAL DECLARATION

**Final Declaration** (verbatim):> "All phases (0-6) complete. No assumptions. No drift.> Tool infrastructure unified: Neo4j logging upgraded, health state tracked,> router refactored to use ExecutorToolRegistry, architecture documented."---

## RISK ASSESSMENT

- **Risk Level**: LOW
- **Breaking Changes**: NONE (API contract unchanged)
- **Files Modified**: 4