---
name: L-Load Audit GMP
overview: "Comprehensive GMP implementation plan to fix 18 identified issues across the L9 Agent Execution Stack: AgentExecutorService, AgentInstance, Self-Reflection, and Kernel Evolution modules."
todos:
  - id: t1-schema-fields
    content: Add tool_calls and tokens_used fields to ExecutionResult in schemas.py
    status: completed
  - id: t2-protocol-align
    content: Add search_packets_by_thread() to SubstrateServiceProtocol
    status: completed
  - id: t3-bind-memory-fix
    content: Fix _bind_memory_context() to use correct protocol method
    status: completed
    dependencies:
      - t2-protocol-align
  - id: t4-dag-field-normalize
    content: Normalize DAG context field access (content vs text)
    status: completed
  - id: t5-enable-hydration
    content: Enable bounded context hydration (last 5 packets)
    status: completed
  - id: t6-truncate-results
    content: Add truncation for large tool results (4000 chars)
    status: completed
  - id: t7-safe-imports
    content: Add safe import pattern for memory_helpers
    status: completed
  - id: t8-persist-reflection
    content: Persist reflection results to memory substrate
    status: completed
  - id: t9-circuit-breaker
    content: Add circuit breaker for consecutive AIOS failures
    status: completed
  - id: t10-evolution-persist
    content: Wire evolution plans to substrate for retrieval
    status: completed
  - id: t11-configurable-thresholds
    content: Make self-reflection thresholds env-configurable
    status: completed
  - id: t12-populate-toolcalls
    content: Populate tool_calls and tokens_used in ExecutionResult
    status: completed
    dependencies:
      - t1-schema-fields
---

# GMP-EXEC-AUDIT: L9 Agent Execution Stack Alignment

**GMP ID:** GMP-EXEC-AUDIT
**Tier:** RUNTIME_TIER (touches core/agents/, core/aios/)
**Risk Level:** HIGH (core execution path)
**Estimated Effort:** 8-12 hours across 3 phases

---

## Executive Summary

Comprehensive audit identified **18 issues** across the L9 Agent Execution Stack:
- **10 CRITICAL** (breaking functionality, data loss, silent failures)
- **5 MEDIUM** (incomplete features, missing integrations)
- **3 LOW** (code quality, configurability)

Primary files affected:
- [`core/agents/executor.py`](core/agents/executor.py) (1622 lines) - 8 issues
- [`core/agents/agent_instance.py`](core/agents/agent_instance.py) (508 lines) - 3 issues
- [`core/agents/selfreflection.py`](core/agents/selfreflection.py) (425 lines) - 2 issues
- [`core/agents/kernelevolution.py`](core/agents/kernelevolution.py) (401 lines) - 2 issues
- [`core/agents/schemas.py`](core/agents/schemas.py) (386 lines) - 1 issue

---

## Critical Issues Summary

| ID | Issue | File | Severity | Fix |
|----|-------|------|----------|-----|
| C1 | `search_packets_by_thread()` not in protocol | executor.py:540 | CRITICAL | Align to protocol method |
| C2 | `result.tool_calls` missing from ExecutionResult | executor.py:1498 | CRITICAL | Add field to schema |
| C3 | Context hydration disabled (breaks continuity) | executor.py:791-830 | CRITICAL | Enable with safety bounds |
| C4 | `memory_search()` import may fail | executor.py:558 | CRITICAL | Safe import pattern |
| C5 | DAG uses `payload.text` vs `payload.content` | agent_instance.py:407 | CRITICAL | Normalize field access |
| C6 | Reflection results not persisted | executor.py:1469 | CRITICAL | Write to substrate |
| C7 | Evolution plans not actionable | kernelevolution.py | CRITICAL | Wire to GMP system |
| C8 | No circuit breaker in execution loop | executor.py:836 | CRITICAL | Add failure tracking |
| C9 | `tokens_used` not in ExecutionResult | schemas.py | CRITICAL | Add field |
| C10 | Tool results not truncated | agent_instance.py:334 | CRITICAL | Add size limits |

---

## Phase 1: Schema and Protocol Alignment

**Goal:** Fix data model mismatches that cause runtime errors.

### [T1] Add `tool_calls` and `tokens_used` to ExecutionResult

**File:** `/Users/ib-mac/Projects/L9/core/agents/schemas.py`
**Lines:** 280-310 (ExecutionResult class)
**Action:** Insert
**Target:** `ExecutionResult` class
**Change:** Add `tool_calls: Optional[List[ToolCallResult]] = None` and `tokens_used: Optional[int] = None` fields
**Gate:** py_compile
**Imports:** NONE (ToolCallResult already imported)

### [T2] Align SubstrateServiceProtocol with actual service

**File:** `/Users/ib-mac/Projects/L9/core/agents/executor.py`
**Lines:** 215-249 (SubstrateServiceProtocol)
**Action:** Replace
**Target:** `SubstrateServiceProtocol`
**Change:** Add `search_packets_by_thread()` method to protocol matching actual substrate_service API
**Gate:** py_compile
**Imports:** NONE

### [T3] Fix `_bind_memory_context()` to use protocol method

**File:** `/Users/ib-mac/Projects/L9/core/agents/executor.py`
**Lines:** 540-548
**Action:** Replace
**Target:** `_bind_memory_context()`
**Change:** Use `search_packets(thread_id=UUID(task_id), limit=10)` instead of non-existent `search_packets_by_thread()`
**Gate:** lint
**Imports:** NONE

---

## Phase 2: Context Assembly and Memory Integration

**Goal:** Fix DAG context injection and enable context hydration.

### [T4] Normalize DAG context field access

**File:** `/Users/ib-mac/Projects/L9/core/agents/agent_instance.py`
**Lines:** 405-410
**Action:** Replace
**Target:** `_build_dag_context_section()`
**Change:** Access `payload.get("content") or payload.get("text", "")` for backward compatibility
**Gate:** lint
**Imports:** NONE

### [T5] Enable bounded context hydration

**File:** `/Users/ib-mac/Projects/L9/core/agents/executor.py`
**Lines:** 791-830
**Action:** Replace
**Target:** `_hydrate_context()`
**Change:** Add last 5 relevant packets to instance history with role='system' for context
**Gate:** lint
**Imports:** NONE

### [T6] Truncate large tool results

**File:** `/Users/ib-mac/Projects/L9/core/agents/agent_instance.py`
**Lines:** 330-338
**Action:** Replace
**Target:** `add_tool_result()`
**Change:** Truncate result content to 4000 chars max with "[TRUNCATED]" marker
**Gate:** lint
**Imports:** NONE

### [T7] Safe import for memory_helpers

**File:** `/Users/ib-mac/Projects/L9/core/agents/executor.py`
**Lines:** 557-585
**Action:** Wrap
**Target:** `memory_search` imports
**Change:** Use try/except ImportError with fallback to empty dict
**Gate:** py_compile
**Imports:** NONE

---

## Phase 3: Self-Reflection and Evolution Wiring

**Goal:** Connect self-reflection to memory persistence and kernel evolution to GMP.

### [T8] Persist reflection results to substrate

**File:** `/Users/ib-mac/Projects/L9/core/agents/executor.py`
**Lines:** 1516-1530
**Action:** Insert
**Target:** `_run_self_reflection()` after `analyze_task_execution()`
**Change:** Write reflection result packet with `packet_type="agent.reflection.result"`
**Gate:** lint
**Imports:** NONE

### [T9] Add circuit breaker for AIOS failures

**File:** `/Users/ib-mac/Projects/L9/core/agents/executor.py`
**Lines:** 920-970 (execution loop)
**Action:** Insert
**Target:** `_run_execution_loop()` before AIOS call
**Change:** Track consecutive failures, break after 3 with ESCALATE status
**Gate:** lint
**Imports:** NONE

### [T10] Wire evolution plans to memory for retrieval

**File:** `/Users/ib-mac/Projects/L9/core/agents/kernelevolution.py`
**Lines:** 292-336
**Action:** Insert
**Target:** `create_evolution_plan()` after plan creation
**Change:** Add optional `substrate_service` param to persist plan packet
**Gate:** lint
**Imports:** `from memory.substrate_models import PacketEnvelopeIn`

---

## Phase 4: Configuration and Quality

**Goal:** Make thresholds configurable and fix code quality issues.

### [T11] Make self-reflection thresholds configurable

**File:** `/Users/ib-mac/Projects/L9/core/agents/selfreflection.py`
**Lines:** 1-30
**Action:** Insert
**Target:** Module constants section
**Change:** Add env-based config: `ITERATION_THRESHOLD`, `TOKEN_THRESHOLD`, `TOOL_FAILURE_THRESHOLD`
**Gate:** lint
**Imports:** `import os`

### [T12] Populate tool_calls in ExecutionResult

**File:** `/Users/ib-mac/Projects/L9/core/agents/executor.py`
**Lines:** 1080-1088
**Action:** Replace
**Target:** `ExecutionResult` construction at end of `_run_execution_loop()`
**Change:** Collect tool_calls from instance and add to result along with `tokens_used=instance.total_tokens`
**Gate:** lint
**Imports:** NONE

---

## Validation Plan

After implementation, validate:

1. **Unit Tests:** Run existing test suite
   ```bash
   pytest tests/core/agents/ -v
   ```

2. **Integration Test:** Execute L task end-to-end
   - Verify context hydration works
   - Verify tool results are truncated
   - Verify reflection results persist

3. **Schema Validation:**
   ```bash
   python -m py_compile core/agents/schemas.py
   python -m py_compile core/agents/executor.py
   ```

---

## L9 Invariant Check

| Invariant File | Touched? | Justification |
|----------------|----------|---------------|
| docker-compose.yml | NO | - |
| kernel_loader.py | NO | - |
| executor.py | YES | Core execution fixes (non-breaking, additive) |
| memory_substrate_service.py | NO | - |
| websocket_orchestrator.py | NO | - |

---

## Rollback Strategy

All changes are additive or fix obvious bugs. Rollback via git:
```bash
git checkout HEAD~1 -- core/agents/executor.py core/agents/agent_instance.py
git checkout HEAD~1 -- core/agents/schemas.py core/agents/selfreflection.py
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Context hydration causes loops | LOW | HIGH | Bound to 5 packets max |
| Tool truncation loses critical data | LOW | MEDIUM | Log when truncation occurs |
| Schema changes break clients | LOW | MEDIUM | Fields are Optional |
