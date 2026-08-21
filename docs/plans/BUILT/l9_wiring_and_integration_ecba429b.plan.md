---
name: L9 Wiring and Integration
overview: "Execute the 7-question action plan: fix audit scripts, wire DTB with full memory adapter, wire API orphans, and integrate IR engine -- all without breaking existing functionality."
todos:
  - id: q1-noop
    content: "Q1: Confirm get_vector_config stays removed from __all__ (no action needed)"
    status: completed
  - id: q2-sdk-docstring
    content: "Q2: Add clarifying docstring to sdk/__init__.py explaining it's an internal facade"
    status: completed
  - id: q3-triage-fix
    content: "Q3: Fix triage_dead_code.py to count internal package refs and add INTERNAL_ONLY reclassification + DYNAMIC_LOAD category for Q5"
    status: completed
  - id: q7-twilio-register
    content: "Q7: Add router_registry.register() to api/webhook_twilio.py"
    status: completed
  - id: q7-wire-orphans
    content: "Q7: Add orphan router imports to api/server.py before wire_all()"
    status: completed
  - id: q6-adapter
    content: "Q6: Create domain_tensor_bridge/l9_memory_adapter.py with full L9 service mappings"
    status: completed
  - id: q6-memory-bridge
    content: "Q6: Modify domain_tensor_bridge/memory_bridge.py to accept L9MemoryAdapter via DI"
    status: completed
  - id: q6-executor
    content: "Q6: Wire DTB AnalogicalReasoner into core/agents/executor.py (feature-flagged)"
    status: completed
  - id: q6-foresight
    content: "Q6: Wire DTB CausalReasoner into core/l_agent_runtime/foresight_engine.py"
    status: completed
  - id: q6-governance
    content: "Q6: Wire DTB ReflectiveReasoner into core/governance/engine.py"
    status: completed
  - id: q6-memory-dag
    content: "Q6: Add analogical_enrichment_node to memory/substrate_dag.py (feature-flagged)"
    status: completed
  - id: q4-document
    content: "Q4: Document IR engine integration path for /gmp and /spec commands"
    status: completed
isProject: false
---

# L9 Wiring and Integration Plan

Based on the deep investigation of Q1-Q7, here is the execution plan organized by risk tier (safest first).

---

## Q1: `get_vector_config` in memory -- Keep Internal

**Decision:** Keep it removed from `__all__`. It's a pipeline-internal helper used only by `substrate_repository.py`. If external consumers need vector config, they should go through the retrieval API, not configure HNSW directly.

**Action:** None. Already correct after the `fix_internal_only_exports.py` run.

---

## Q2: SDK Package -- Document as Internal Facade

**Decision:** SDK is an internal convenience layer wrapping L9 subsystems. Its 16 zero-reference symbols are the public facade surface. They become useful when external integrators (or new agents) want simplified access.

**Action:** Add a docstring to `sdk/__init__.py` clarifying purpose. No wiring changes needed -- it's intentionally a "pull when needed" package.

---

## Q3: Audit Script Fix + UnifiedController Status

### Fix Triage Script False Positives

The triage script flags `world_model` and `orchestration` symbols as ZERO_REF because `rg` word-boundary matching misses internal usage within the same package.

**Fix in** `[tools/validation/triage_dead_code.py](tools/validation/triage_dead_code.py)`:

- When counting references for a symbol, count references *within* the package (excluding the definition file and `__init__.py`)
- Reclassify symbols with internal-only refs as `INTERNAL_ONLY` not `ZERO_REF`
- Add `--include-internal` flag to optionally show internal-only symbols

### UnifiedController Status

**Status: COMPLETE** (v2.0.0, active). It is the GOD-MODE top-level controller that coordinates:

- Task routing, IR pipeline (NL -> IR -> Plan), simulation, cell collaboration, execution, reflection
- Fully integrates with IR engine via lazy imports (SemanticCompiler, IRValidator, ConstraintChallenger, etc.)
- Exported from `orchestration/__init__.py`

No action needed -- it's wired and functional.

---

## Q4: IR Engine Leverage for `/gmp` and `/spec`

### How IR Engine Benefits Commands

The IR engine's `SemanticCompiler` converts natural language to `IRGraph` (structured intent representation). This directly benefits:

- `**/gmp**`: Phase 0 plan generation can use `compile_only()` to produce a validated IR plan before execution
- `**/spec**`: Spec generation can use `SemanticCompiler` to extract structured requirements from NL descriptions

### Integration Points

The `UnifiedController` already exposes:

- `compile_only(text, context)` -- compile NL to IR without execution
- `plan_only(text, context)` -- generate execution plan without running it

**Action:** Wire `compile_only` into `/gmp` Phase 0 and `/spec` command handlers. This is a future enhancement -- document the integration path but don't wire yet (commands work without it).

---

## Q5: Group 5 False Positives (agents, mac_agent)

These appear on the zero-ref list because they are **dynamically loaded** (agent configs reference them by string name) or **event-driven** (triggered by webhooks/WebSocket, not direct imports).

**Action:** Add a `DYNAMIC_LOAD` category to the triage script. Symbols in `agents/`, `mac_agent/`, and webhook handlers get this classification instead of ZERO_REF.

---

## Q6: Domain Tensor Bridge -- Full Wire to 4 Integration Points

This is the largest and highest-risk change. DTB's `MemoryBridge` calls methods that don't exist on `MemorySubstrateService`. We need a full adapter.

### Architecture

```
DTB Components          L9 Adapter Layer              L9 Services
--------------          ----------------              -----------
AnalogicalReasoner  ->  L9MemoryAdapter.query_events  ->  substrate_service.query_packets()
CausalReasoner      ->  L9MemoryAdapter.store_event   ->  substrate_service.write_packet()
MemoryBridge        ->  L9MemoryAdapter.redis_get/set  ->  working_memory_service
ReflectiveReasoner  ->  L9MemoryAdapter.cypher_query   ->  graph_client
```

### Files to Create/Modify

1. **CREATE** `domain_tensor_bridge/l9_memory_adapter.py`
  - Class `L9MemoryAdapter` implementing the interface `MemoryBridge` expects
  - Maps: `query_events()` -> `query_packets()`, `store_event()` -> `write_packet()`, `redis_get/set` -> `WorkingMemoryService`, `cypher_query()` -> `graph_client`
  - Remove HyperGraphDB references (not implemented)
2. **MODIFY** `domain_tensor_bridge/memory_bridge.py`
  - Accept `L9MemoryAdapter` via dependency injection instead of raw `MemorySubstrateService`
3. **Integration Point 1: Agent Executor** -- MODIFY `[core/agents/executor.py](core/agents/executor.py)`
  - Add optional DTB reasoning step in the execution loop (gated by feature flag `L9_ENABLE_DTB`)
  - Use `AnalogicalReasoner` to find cross-domain patterns before tool dispatch
4. **Integration Point 2: Foresight Engine** -- MODIFY `[core/l_agent_runtime/foresight_engine.py](core/l_agent_runtime/foresight_engine.py)`
  - Wire `CausalReasoner` into foresight predictions
  - Use causal chains to improve prediction confidence
5. **Integration Point 3: Governance** -- MODIFY `[core/governance/engine.py](core/governance/engine.py)`
  - Wire `ReflectiveReasoner` for policy evaluation enrichment
  - DTB provides additional context for approval decisions
6. **Integration Point 4: Memory Pipeline** -- MODIFY `[memory/substrate_dag.py](memory/substrate_dag.py)`
  - Add optional `analogical_enrichment_node` after `intake_node`
  - Gated by feature flag -- does NOT run unless `L9_ENABLE_DTB_MEMORY=true`
  - Stores DTB insights as new `PacketEnvelope` packets (type `analogical_insight`)

### Safety Constraints

- All DTB integration gated behind `L9_ENABLE_DTB` feature flag (default: `false`)
- DTB failures are non-fatal -- caught and logged, never block the pipeline
- Memory pipeline integration is additive only (new node, doesn't modify existing nodes)
- All DTB results stored as new packets, never mutate existing packets

---

## Q7: API Orphan Wiring

### Wire via Import in server.py

Add imports to `[api/server.py](api/server.py)` before `router_registry.wire_all(app)` to trigger registration:

```python
# Wire orphan routers (they self-register on import)
import api.agent_routes        # /agent endpoints
import api.os_routes           # /os endpoints
import api.webhook_mac_agent   # /mac webhook
import api.world_model_api     # /world-model endpoints
```

### Fix webhook_twilio.py Registration

Add `router_registry.register()` call to `[api/webhook_twilio.py](api/webhook_twilio.py)`, then import it in server.py.

### Utility Files (No Action)

- `api/db.py` -- database helper, not a router
- `api/openapi_config.py` -- config constants, not a router

---

## Execution Order (Risk-Tiered)


| Phase | Items                                            | Risk   | Files                                                     |
| ----- | ------------------------------------------------ | ------ | --------------------------------------------------------- |
| 1     | Q1 (no-op), Q2 (docstring), Q5 (triage category) | Low    | `sdk/__init__.py`, `tools/validation/triage_dead_code.py` |
| 2     | Q3 (fix triage script false positives)           | Low    | `tools/validation/triage_dead_code.py`                    |
| 3     | Q7 (wire API orphans)                            | Medium | `api/server.py`, `api/webhook_twilio.py`                  |
| 4     | Q6 (DTB adapter + 4 integration points)          | High   | 6+ files, feature-flagged                                 |
| 5     | Q4 (document IR engine command integration path) | Low    | Documentation only                                        |
