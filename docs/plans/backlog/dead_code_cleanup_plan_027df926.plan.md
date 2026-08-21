---
name: Dead Code Cleanup Plan
overview: Systematic cleanup of 502 dead code and wiring issues found in the L9 audit. Organized into prerequisites, quick wins, and categorized batches with explicit actions for each finding type.
todos:
  - id: phase0-prereq
    content: Install vulture and ruff, update EXCLUDE_DIRS to exclude _archived, docs, codegen, igor
    status: pending
  - id: phase1-false-pos
    content: Verify archived kernels and codegen specs are excluded from scan, re-run audit
    status: pending
  - id: phase2-routers
    content: "GMP: Wire 26 unwired routers to api/server.py or delete unused"
    status: pending
  - id: phase2-deps
    content: "GMP: Wire 6 unused dependencies in api/dependencies.py or delete"
    status: pending
  - id: phase2-tools
    content: Register AGENT_SELF_MODIFY_TOOL_DEFINITIONS with ToolGraph
    status: pending
  - id: phase3-dataclass
    content: Batch audit 292 unused dataclass fields, delete truly unused, document kept
    status: pending
  - id: phase3-services
    content: "GMP: Wire or delete 12 unwired services"
    status: pending
  - id: phase3-orchestrators
    content: "GMP: Wire or delete 9 unwired orchestrators"
    status: pending
  - id: phase3-background
    content: Audit 33 unwired background tasks, wire or rename
    status: pending
  - id: phase4-events
    content: Wire 2 unwired event handlers
    status: pending
  - id: phase4-pydantic
    content: Use or delete 1 unwired pydantic model
    status: pending
  - id: final-audit
    content: Re-run audit, target under 50 findings
    status: pending
---

# Dead Code and Wiring Cleanup Plan

## Audit Summary

- **Total Findings:** 502
- **Files Scanned:** 760
- **Dataclass Fields Analyzed:** 2,239

| Category | Count | Confidence | Priority |

|----------|-------|------------|----------|

| dataclass_field | 292 | 95% HIGH | MEDIUM |

| unwired_agent | 104 | 70% MEDIUM | LOW (codegen specs) |

| unwired_background | 33 | 60% LOW | MEDIUM |

| unwired_router | 26 | 75% MEDIUM | HIGH |

| unwired_kernel | 16 | 95% HIGH | LOW (archived) |

| unwired_service | 12 | 70% MEDIUM | MEDIUM |

| unwired_orchestrator | 9 | 70% MEDIUM | MEDIUM |

| unwired_dependency | 6 | 85% HIGH | HIGH |

| unwired_event | 2 | 65% LOW | MEDIUM |

| unwired_tool | 1 | 85% HIGH | HIGH |

| unwired_pydantic | 1 | 80% HIGH | MEDIUM |

---

## Phase 0: Prerequisites

### 0.1 Install Missing Tools

```bash
pip install vulture ruff
```

The audit script was updated to use `python -m vulture` but tools still need to be installed.

### 0.2 Fix Scan Exclusions

Update [scripts/audit/find_dead_code.py](scripts/audit/find_dead_code.py) to exclude:

- `_archived` directories (kernels, agents)
- `docs/` directory (contains non-Python files named .py)
- `codegen/` directory (generated specs, not production code)
- `igor/` directory (audit tools, not production)

Add to `EXCLUDE_DIRS`:

```python
EXCLUDE_DIRS = {
    "tests", "_archived", "__pycache__", ".venv", "venv", ".git", 
    "node_modules", "docs", "codegen", "igor"
}
```

### 0.3 Fix False Positive Directories

These directories have `.py` extensions but are actually directories or non-Python:

- `docs/TODO/agent_persistence.py` (directory)
- `docs/DONE/consolidation.py` (directory)

Rename or delete these.

---

## Phase 1: Quick Wins (FALSE POSITIVES)

### 1.1 Exclude Archived Kernels (16 findings)

All 16 "unwired kernels" are in `private/kernels/00_system/_archived/`. These are intentionally archived and should not be flagged.

**Action:** Add `_archived` to exclusions in scan (already in Phase 0.2).

### 1.2 Exclude Codegen Agent Specs (104 findings)

All 104 "unwired agents" are generated specs in `agents/codegenagent/codegen+codegenAgent_specs/`. These are generated artifacts, not production code.

**Action:** Add pattern exclusion for `codegen+codegenAgent_specs` or exclude `agents/codegenagent/` entirely.

---

## Phase 2: HIGH Priority Fixes

### 2.1 Unwired Routers (26 findings)

These routers are defined but not mounted in [api/server.py](api/server.py).

| Router File | Action |

|-------------|--------|

| `api/os_routes.py` | Verify if needed, wire or delete |

| `api/webhook_twilio.py` | Wire to main app |

| `api/webhook_mac_agent.py` | Wire to main app |

| `api/world_model_api.py` | Wire to main app |

| `api/webhook_slack.py` | Wire to main app |

| `api/webhook_waba.py` | Wire to main app |

| `api/agent_routes.py` | Wire to main app |

| `api/tools/router.py` | Wire to main app |

| `api/memory/graph.py` | Wire to main app |

| `api/memory/cache.py` | Wire to main app |

| ... (16 more) | Audit each |

**GMP Required:** Wire all legitimate routers to `api/server.py` via `app.include_router()`.

### 2.2 Unwired Dependencies (6 findings)

All in [api/dependencies.py](api/dependencies.py):

- `get_agent_executor`
- `get_governance_engine`
- `get_neo4j_client`
- `get_redis_client`
- `get_observability_service`
- `get_world_model_service`

**Action:** Either wire these into routes via `Depends()` or delete if unused.

### 2.3 Unwired Tool (1 finding)

`AGENT_SELF_MODIFY_TOOL_DEFINITIONS` in [core/tools/agent_self_modify.py](core/tools/agent_self_modify.py).

**Action:** Register with ToolGraph or delete if not needed.

---

## Phase 3: MEDIUM Priority Fixes

### 3.1 Dataclass Fields (292 findings)

Grouped by file for batch processing:

| File | Unused Fields | Action |

|------|---------------|--------|

| `memory/hybrid_rag.py` | 13 | Audit, delete unused |

| `core/evaluation/evaluator.py` | 9 | Audit, delete unused |

| `memory/schema_introspection.py` | 7 | Audit, delete unused |

| `core/memory/virtual_context.py` | 3 | Audit, delete unused |

| `core/agents/selfreflection.py` | 3 | Audit, delete unused |

| `core/governance/quick_fixes.py` | 3 | Audit, delete unused |

| ... (280+ more in other files) | ... | Batch audit |

**Strategy:** Process file-by-file, remove truly unused fields, document fields kept for API compatibility.

### 3.2 Unwired Services (12 findings)

| Service | File | Action |

|---------|------|--------|

| `FailureAnalyzer` | `core/observability/failures.py` | Wire or delete |

| `MemoryStateManager` | `igor/audit-memory/` | Delete (audit tools) |

| `MemoryTimelineService` | `igor/audit-memory/` | Delete (audit tools) |

| `MemoryCheckpointManager` | `igor/audit-memory/` | Delete (audit tools) |

| `CursorExecutorService` | `agents/cursor/integrations/` | Wire or delete |

| `TwilioAdapterService` | `api/adapters/twilio_adapter/` | Wire or delete |

| `CalendarAdapterService` | `api/adapters/calendar_adapter/` | Wire or delete |

| `EmailAdapterService` | `api/adapters/email_adapter/` | Wire or delete |

| ... | ... | ... |

### 3.3 Unwired Orchestrators (9 findings)

| Orchestrator | File | Action |

|--------------|------|--------|

| `MetaOrchestratorInterface` | `orchestrators/meta/interface.py` | Wire or delete |

| `MetaOrchestrator` | `orchestrators/meta/orchestrator.py` | Wire or delete |

| `WorldModelInterface` | `orchestrators/world_model/interface.py` | Wire or delete |

| `WorldModelOrchestrator` | `orchestrators/world_model/orchestrator.py` | Wire or delete |

| `ReasoningInterface` | `orchestrators/reasoning/interface.py` | Wire or delete |

| `ResearchSwarmInterface` | `orchestrators/research_swarm/interface.py` | Wire or delete |

| `EvolutionInterface` | `orchestrators/evolution/interface.py` | Wire or delete |

| `EvolutionOrchestrator` | `orchestrators/evolution/orchestrator.py` | Wire or delete |

| `AgentExecutionInterface` | `orchestrators/agent_execution/interface.py` | Wire or delete |

### 3.4 Unwired Background Tasks (33 findings)

Functions named `*_async`, `*_background`, `*_task` but never scheduled.

| File | Count | Action |

|------|-------|--------|

| `runtime/gmp_worker.py` | 6 | Wire via `add_task()` or rename |

| `core/singleton_registry.py` | 3 | False positives (async methods) |

| `runtime/gmp_approval.py` | 3 | Wire or delete |

| `core/observability/l9_integration.py` | 2 | Wire or delete |

| ... | ... | ... |

---

## Phase 4: LOW Priority / Review

### 4.1 Unwired Events (2 findings)

- `startup_health` in `api/server.py:1898`
- `shutdown_runtime` in `services/research/graph_runtime.py:175`

**Action:** Verify these are decorated with `@app.on_event()` or wire them.

### 4.2 Unwired Pydantic Model (1 finding)

In `api/world_model_api.py` - a model defined but never used in routes.

**Action:** Use in route signatures or delete.

---

## Execution Strategy

```mermaid
flowchart TD
    P0[Phase 0: Prerequisites]
    P1[Phase 1: Quick Wins]
    P2[Phase 2: HIGH Priority]
    P3[Phase 3: MEDIUM Priority]
    P4[Phase 4: LOW Priority]
    
    P0 --> P1
    P1 --> P2
    P2 --> P3
    P3 --> P4
    
    P0 --> |Install tools| TOOLS[pip install vulture ruff]
    P0 --> |Fix exclusions| EXCL[Update EXCLUDE_DIRS]
    
    P1 --> |120 false positives| FP[Exclude archived + codegen]
    
    P2 --> |33 critical| WIRE[Wire routers + deps + tools]
    
    P3 --> |313 findings| AUDIT[Audit and clean per file]
    
    P4 --> |3 findings| VERIFY[Verify and fix]
```

---

## Estimated Effort

| Phase | Findings | Effort | GMPs |

|-------|----------|--------|------|

| Phase 0 | N/A | 30 min | 0 |

| Phase 1 | 120 | 15 min | 0 |

| Phase 2 | 33 | 2-3 hours | 2-3 |

| Phase 3 | 313 | 4-6 hours | 5-8 |

| Phase 4 | 3 | 30 min | 1 |

**Total:** ~8-10 hours across multiple GMPs

---

## Re-run Audit After Each Phase

After completing each phase, re-run:

```bash
python3 scripts/audit/find_dead_code.py --output reports/dead_code_audit_$(date +%Y%m%d_%H%M%S).json
```

Target: Reduce findings from 502 to under 50 (legitimate edge cases).