---
name: Agent Init Paradigm Shift
overview: Implement L-CTO Agent Initialization Paradigm Shift by HARVESTING existing production-ready code from L-Bootstrap and Implementation Suite documents, then wiring into L9. This replaces 32 weeks of generation with 2-3 weeks of extraction and integration.
todos:
  - id: gmp-l0
    content: HARVEST bootstrap from L-Bootstrap, create 10 files, wire server.py
    status: pending
  - id: gmp-l1
    content: Create approval_manager.py, enhance ToolDefinition, add executor gate
    status: pending
  - id: gmp-l2
    content: Create memory_tools.py with memory_search/memory_write
    status: pending
  - id: gmp-l4
    content: Wire GMP/git pending approval workflow
    status: pending
  - id: gmp-l5
    content: HARVEST virtual_context.py from Implementation Suite
    status: pending
---

# Agent Initialization Paradigm Shift - Harvest and Wire

## Executive Summary

The code already exists in the L-Bootstrap and Implementation Suite documents. Instead of generating 2000+ lines manually, we HARVEST and adapt:

| Source Document | Contains | Lines | Harvest Target |
|-----------------|----------|-------|----------------|
| [L9-Agent-Bootstrap-Architecture.md](docs/__01-04-2026/__Agent Initialization - Paradigm Shift/L-Bootstrap/L9-Agent-Bootstrap-Architecture.md) | 10 bootstrap phase files + orchestrator | ~1000 | `core/agents/bootstrap/` |
| [L9-Implementation-Suite-Ready-to-Deploy.md](docs/__01-04-2026/__Agent Initialization - Paradigm Shift/L9-Implementation-Suite-Ready-to-Deploy.md) | 4 module implementations | ~1800 | `core/coordination/`, `core/tools/`, `core/memory/`, `core/evaluation/` |
| [C-Execution-Guide-GMP-Prometheus.md](docs/__01-04-2026/__L9-Telemetry/C-Execution-Guide-GMP-Prometheus.md) | Memory tools, approval patterns | ~500 | `core/governance/`, `tools/` |

**Prometheus integration (GMP-L.3) is ALREADY COMPLETE** per [Report_GMP-PROMETHEUS-GRAFANA.md](reports/Report_GMP-PROMETHEUS-GRAFANA.md).

---

## Architecture Flow

```mermaid
flowchart TD
    subgraph bootstrap [GMP-L.0: Agent Bootstrap Ceremony]
        P0[Phase 0: Validate Blueprint]
        P1[Phase 1: Load Kernels]
        P2[Phase 2: Instantiate Agent]
        P3[Phase 3: Bind Kernels]
        P4[Phase 4: Load Identity]
        P5[Phase 5: Bind Tools]
        P6[Phase 6: Wire Governance]
        P7[Phase 7: Verify and Lock]
        P0 --> P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7
    end
    
    subgraph modules [Modules Enabled at Bootstrap]
        M1[Event Queue]
        M2[Tool Audit]
        M3[Virtual Context]
        M4[Evaluator]
    end
    
    P7 -->|READY| modules
    modules --> Executor
    Executor -->|approval_gate| ApprovalManager
    ApprovalManager -->|pending| IgorApproval
</mermaid>

---

## GMP Execution Sequence (5 GMPs, Sequential)

### GMP-L.0: Agent Bootstrap (HARVEST from L-Bootstrap)

**Source**: [L9-Agent-Bootstrap-Architecture.md](docs/__01-04-2026/__Agent Initialization - Paradigm Shift/L-Bootstrap/L9-Agent-Bootstrap-Architecture.md)

**Action**: Extract and create 10 files in `core/agents/bootstrap/`:
- `__init__.py`
- `phase_0_validate.py`
- `phase_1_load_kernels.py`
- `phase_2_instantiate.py`
- `phase_3_bind_kernels.py`
- `phase_4_load_identity.py`
- `phase_5_bind_tools.py`
- `phase_6_wire_governance.py`
- `phase_7_verify_and_lock.py`
- `orchestrator.py`

**Wire into**: [api/server.py](api/server.py) lifespan startup

**Success Criteria**: L boots with 10 kernels active, tools registered, identity in memory

---

### GMP-L.1: Tool Metadata and Approval Manager

**Source**: Patterns from Execution Guide + existing [core/tools/registry_adapter.py](core/tools/registry_adapter.py)

**Create**:
- `core/governance/approval_manager.py` - Check/create Igor approvals
- Enhance `ToolDefinition` with `requires_igor_approval`, `risk_level`, `scope`

**Wire into**: [core/agents/executor.py](core/agents/executor.py) - add approval gate before tool dispatch

**Gate Logic**:

```python
if tool_def.requires_igor_approval:
    approval = await approval_manager.check_approval(task_id)
    if not approval:
        return pending_result(task_id)  # Enqueue for Igor
```

---

### GMP-L.2: Memory Tools

**Source**: Patterns from Execution Guide section "Critical Gap #3"

**Create**: `core/tools/memory_tools.py`
- `memory_search(segment, query, limit)` - Search agent memory
- `memory_write(segment, payload)` - Write to agent memory

**Segments**: governance_meta, project_history, tool_audit, session_context

**Register**: Add to tool registry with low risk, no approval required

---

### GMP-L.3: Prometheus Metrics

**STATUS: ALREADY COMPLETE**

Per [Report_GMP-PROMETHEUS-GRAFANA.md](reports/Report_GMP-PROMETHEUS-GRAFANA.md):
- `/metrics` endpoint exists
- `telemetry/memory_metrics.py` exists
- Grafana dashboard at `grafana/dashboards/l9-tool-observability.json`

**Action**: Verify it works, skip to GMP-L.4

---

### GMP-L.4: GMP/Git Pending Approval Workflow

**Depends on**: GMP-L.1 (approval_manager)

**Modify**:
- [core/agents/executor.py](core/agents/executor.py) - Check approval before GMPRUN, GITCOMMIT tools
- Create `tools/gmp.py`, `tools/git.py` with `requires_igor_approval=True`

**Flow**:
1. L proposes GMP run
2. Executor checks approval gate
3. No approval -> enqueue as PENDING
4. Igor approves via API/Slack
5. Task resumes

---

### GMP-L.5: Virtual Context Management (HARVEST from Implementation Suite)

**Source**: [L9-Implementation-Suite-Ready-to-Deploy.md](docs/__01-04-2026/__Agent Initialization - Paradigm Shift/L9-Implementation-Suite-Ready-to-Deploy.md) - MODULE 3

**Create**: `core/memory/virtual_context.py`
- `VirtualContextManager` class
- `MemoryConsolidationService` class
- Tier management (main/working/archival)
- Page fault handler for on-demand archival retrieval

**Wire into**: Bootstrap Phase 5 or as module init in lifespan

---

## Feature Flags (.env)

```bash
L9_NEW_AGENT_INIT=false       # Toggle new bootstrap vs legacy
MODULE_1_EVENT_QUEUE=false    # Enable after GMP-L.0
MODULE_2_TOOL_AUDIT=true      # Already wired with Prometheus
MODULE_3_VIRTUAL_CONTEXT=false # Enable after GMP-L.5
MODULE_4_EVALUATOR=false      # Future
```

---

## Timeline (2-3 weeks vs original 32 weeks)

| Week | Day | GMP | Action |
|------|-----|-----|--------|
| 1 | 1-2 | L.0 | Harvest bootstrap files, create `core/agents/bootstrap/` |
| 1 | 3 | L.0 | Wire into server.py, test L boots with READY status |
| 1 | 4-5 | L.1 | Create approval_manager.py, add gate to executor |
| 2 | 1-2 | L.2 | Create memory_tools.py, register in tool graph |
| 2 | 3 | L.3 | Verify Prometheus works (already done) |
| 2 | 4-5 | L.4 | Wire GMP/git pending approval, test escalation |
| 3 | 1-3 | L.5 | Harvest virtual_context.py, wire tier management |

---

## Key Files to Modify

| File | Change |
|------|--------|
| [api/server.py](api/server.py) | Add bootstrap orchestrator call in lifespan |
| [core/agents/executor.py](core/agents/executor.py) | Add approval gate before tool dispatch |
| [core/tools/registry_adapter.py](core/tools/registry_adapter.py) | Enhance ToolDefinition with governance fields |

## Key Files to Create

| Path | Source |
|------|--------|
| `core/agents/bootstrap/*.py` (10 files) | HARVEST from L-Bootstrap |
| `core/governance/approval_manager.py` | Pattern from Execution Guide |
| `core/tools/memory_tools.py` | Pattern from Execution Guide |
| `core/memory/virtual_context.py` | HARVEST from Implementation Suite |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| L boots with READY status | All 10 kernels active |
| Tools registered in Neo4j | 20+ tools with governance metadata |
| Approval gate works | GMP/git enqueue as pending without approval |
| Memory tools work | L can query/write own memory |
| Virtual context works | 1M+ token conversations possible |

---

## Risk Mitigation

- **Feature flag**: `L9_NEW_AGENT_INIT=false` allows instant rollback
- **Parallel paths**: Old init continues until new proven
- **Atomic bootstrap**: All phases succeed or rollback