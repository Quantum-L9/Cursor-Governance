---
name: Tool Executor Wiring Fix
overview: Fix the gap between 73 tool definitions and 36 registered executors by adding @register_tool decorators to existing implementations in l_tools.py and implementing 2 missing core tools (perplexity_search, http_request).
todos:
  - id: add-decorators-memory
    content: Add @register_tool decorators to 20 memory tools in l_tools.py
    status: pending
  - id: add-decorators-worldmodel
    content: Add @register_tool decorators to 9 world model tools in l_tools.py
    status: pending
  - id: add-decorators-governance
    content: Add @register_tool decorators to 3 governance tools in l_tools.py
    status: pending
  - id: add-decorators-introspection
    content: Add @register_tool decorators to 11 introspection tools in l_tools.py
    status: pending
  - id: add-decorators-other
    content: Add @register_tool decorators to neo4j_query, kernel_read, simulation_execute
    status: pending
  - id: fix-long-plan
    content: Add @register_tool with name='long_plan_execute' and 'long_plan_simulate' to long_plan_tool.py
    status: pending
  - id: fix-symbolic
    content: Fix duplicate decorators and add async symbolic_optimize wrapper
    status: pending
  - id: implement-perplexity
    content: Implement perplexity_search executor using PerplexityEnricher
    status: pending
  - id: implement-http
    content: Implement http_request executor using aiohttp
    status: pending
  - id: fix-simulation-name
    content: Change simulation to simulation_execute in registry_adapter.py
    status: pending
  - id: update-packages
    content: Add runtime.long_plan_tool and uncomment runtime.redis_tools in tool_packages.py
    status: pending
  - id: validate
    content: "Run validation: check executor count, startup logs, /tools/health endpoint"
    status: pending
isProject: false
---

# Tool Executor Wiring Fix Plan

## Problem Analysis

**Current State:**

- 73 tool definitions in `core/tools/registry_adapter.py`
- Only 36 tools have `@register_tool` decorators
- 68 async executor functions exist in `runtime/l_tools.py` but lack decorators
- Result: "No executor found for tool" warnings at startup

**Root Cause:**
The `l_tools.py` functions exist but aren't decorated with `@register_tool`, so they don't appear in `TOOL_EXECUTORS` dictionary when `register_l_cto_tools()` looks them up.

## Gap Analysis

### Category 1: Implementations Exist, Missing Decorators (66 tools)

All these functions exist in `runtime/l_tools.py` but need `@register_tool` decorators:

**Memory Tools (18):**
`memory_search`, `memory_write`, `memory_get_packet`, `memory_query_packets`, `memory_search_by_thread`, `memory_search_by_type`, `memory_get_events`, `memory_get_reasoning_traces`, `memory_get_facts`, `memory_write_insight`, `memory_embed_text`, `memory_hybrid_search`, `memory_fetch_lineage`, `memory_fetch_thread`, `memory_fetch_facts_api`, `memory_fetch_insights`, `memory_gc_stats`, `memory_get_checkpoint`, `memory_trigger_world_model_update`, `memory_health_check`

**World Model Tools (8):**
`world_model_query`, `world_model_get_entity`, `world_model_list_entities`, `world_model_snapshot`, `world_model_list_snapshots`, `world_model_send_insights`, `world_model_get_state_version`, `world_model_restore`, `world_model_list_updates`

**Governance Tools (3):**
`gmp_run`, `git_commit`, `mac_agent_exec_task`

**Introspection Tools (11):**
`tools_list_all`, `tools_list_enabled`, `tools_get_metadata`, `tools_get_schema`, `tools_get_by_type`, `tools_get_for_role`, `tools_get_api_dependents`, `tools_get_dependencies`, `tools_get_blast_radius`, `tools_detect_circular_deps`, `tools_get_catalog`

**Neo4j Tools (1):**
`neo4j_query`

**Kernel Tools (1):**
`kernel_read`

**Simulation Tools (1):**
`simulation_execute` (note: definition says `simulation`, function is `simulation_execute`)

### Category 2: Name Mismatch (2 tools)


| Definition Name      | Function Name             | Location                    |
| -------------------- | ------------------------- | --------------------------- |
| `long_plan_execute`  | `long_plan_execute_tool`  | `runtime/long_plan_tool.py` |
| `long_plan_simulate` | `long_plan_simulate_tool` | `runtime/long_plan_tool.py` |


### Category 3: Missing Implementations (2 tools)


| Tool Name           | Category    | Action              |
| ------------------- | ----------- | ------------------- |
| `perplexity_search` | research    | Create new executor |
| `http_request`      | integration | Create new executor |


### Category 4: Sync Function Needs Async Wrapper (1 tool)

`symbolic_optimize` in `core/tools/symbolic_tool.py` is sync, needs async wrapper

## Implementation Strategy

### Phase 1: Add Decorators to l_tools.py

Add `@register_tool` decorators to all 66 existing functions in [runtime/l_tools.py](runtime/l_tools.py).

Pattern for each tool:

```python
@register_tool(
    name="memory_search",
    category="memory",
    priority=10,
    description="Search L's memory substrate using semantic search. Returns ranked results with confidence scores."
)
async def memory_search(...):
```

### Phase 2: Fix Long Plan Tools

In [runtime/long_plan_tool.py](runtime/long_plan_tool.py):

- Add `@register_tool(name="long_plan_execute", ...)` to `long_plan_execute_tool`
- Add `@register_tool(name="long_plan_simulate", ...)` to `long_plan_simulate_tool`

### Phase 3: Fix Symbolic Tools

In [core/tools/symbolic_tool.py](core/tools/symbolic_tool.py):

- Remove duplicate `@register_tool` decorators (lines 258-259, 288-289)
- Add async wrapper for `symbolic_optimize`

### Phase 4: Implement Missing Tools

In [runtime/l_tools.py](runtime/l_tools.py), add:

```python
@register_tool(
    name="perplexity_search",
    category="research",
    priority=10,
    description="Search and synthesize information using Perplexity AI. Returns structured research results with citations."
)
async def perplexity_search(
    query: str,
    focus: str = "general",
    **kwargs: Any,
) -> dict[str, Any]:
    """Use Perplexity API for web research."""
    # Implementation using runtime/superprompt_emitter.py::PerplexityEnricher
```

```python
@register_tool(
    name="http_request",
    category="integration",
    priority=10,
    description="Make HTTP requests to external APIs. Supports GET, POST, PUT, DELETE, PATCH with headers and body."
)
async def http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 30,
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute HTTP request using aiohttp."""
```

### Phase 5: Fix Simulation Name Mismatch

In [core/tools/registry_adapter.py](core/tools/registry_adapter.py) line 3451:

- Change `name="simulation"` to `name="simulation_execute"` to match the function name

### Phase 6: Update Tool Packages

In [runtime/tool_packages.py](runtime/tool_packages.py):

- Add `"runtime.long_plan_tool"` to TOOL_PACKAGES
- Uncomment `"runtime.redis_tools"` (it has 13 properly decorated tools)

## Files to Modify


| File                                                             | Changes                                                       |
| ---------------------------------------------------------------- | ------------------------------------------------------------- |
| [runtime/l_tools.py](runtime/l_tools.py)                         | Add ~66 `@register_tool` decorators + 2 new implementations   |
| [runtime/long_plan_tool.py](runtime/long_plan_tool.py)           | Add 2 `@register_tool` decorators with correct names          |
| [core/tools/symbolic_tool.py](core/tools/symbolic_tool.py)       | Fix duplicate decorators, add async `symbolic_optimize`       |
| [runtime/tool_packages.py](runtime/tool_packages.py)             | Add `runtime.long_plan_tool`, uncomment `runtime.redis_tools` |
| [core/tools/registry_adapter.py](core/tools/registry_adapter.py) | Fix `simulation` -> `simulation_execute` name                 |


## 10X Tool Descriptions

Each tool description must be:

- **Precise**: Exactly what it does, no ambiguity
- **Actionable**: When to use it
- **Complete**: Parameters and return values implied
- **Concise**: Under 100 characters preferred

Example transformations:

- Before: `"Search L's memory substrate using semantic search"`
- After: `"Semantic search across memory. Returns ranked PacketEnvelopes with similarity scores. Use for context retrieval."`

## Validation

After implementation:

1. Run `python -c "from runtime.tool_registry import get_tool_executors; print(len(get_tool_executors()))"`
  - Expected: 73+ tools
2. Check startup logs for "No executor found" warnings
  - Expected: 0 warnings
3. Run `/tools/health` endpoint
  - Expected: 73 tools registered

