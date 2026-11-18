---
name: Fix C1 Deployment Blockers
overview: "Fix 4 critical blockers preventing full L9 functionality on C1: Neo4j connection, duplicate tool registration, and governance context for background tasks."
todos:
  - id: commit-neo4j-fix
    content: Commit and push existing GMP-132 Neo4j fix (api/server.py, memory/graph_client.py)
    status: completed
  - id: fix-duplicate-tools
    content: Remove @register_tool decorator for memory_write from runtime/l_tools.py line 107
    status: completed
  - id: fix-wm-governance
    content: Add governance context wrapper in world_model/runtime.py fetch_packets()
    status: completed
  - id: fix-seed-governance
    content: Add governance context wrapper in world_model/seed_loader.py write_packet_to_substrate()
    status: completed
  - id: deploy-verify
    content: Pull to C1, rebuild l9-api, verify all errors resolved
    status: completed
isProject: false
---

# Fix C1 Deployment Blockers

## Problem Summary

The L9 deployment on C1 has 4 critical blockers:

1. Neo4j connection fails despite healthy container
2. Duplicate tool registration crashes tool graph
3. World Model runtime lacks governance context for query_packets
4. Seed loader lacks governance context for write_packet

## Current Status (UPDATED)


| Issue                           | Local Status                                          | Committed        | On C1              |
| ------------------------------- | ----------------------------------------------------- | ---------------- | ------------------ |
| Neo4j (GMP-132)                 | DONE - api/server.py, memory/graph_client.py modified | NO - uncommitted | NO                 |
| Duplicate tools (memory_search) | DONE                                                  | YES (faa41951)   | NO - needs rebuild |
| Duplicate tools (memory_write)  | NOT DONE                                              | NO               | NO                 |
| Governance context (WM + Seed)  | NOT DONE                                              | NO               | NO                 |


**Key Finding:** GMP-132 Neo4j fix exists locally but was never committed/pushed.

## Architecture Overview

```mermaid
flowchart TB
    subgraph api [API Startup]
        A[lifespan] --> B[init_neo4j_client]
        A --> C[register_l_tools]
        A --> D[WorldModelRuntime]
    end
    
    subgraph neo4j_issue [Issue 1: Neo4j]
        B --> E{5 retries}
        E -->|all fail| F[graph features disabled]
    end
    
    subgraph tool_issue [Issue 2: Tools]
        C --> G[import l_tools.py]
        G --> H["@register_tool memory_write"]
        H --> I[DuplicateRegistrationError]
    end
    
    subgraph gov_issue [Issues 3+4: Governance]
        D --> J[run_forever loop]
        J --> K[fetch_packets]
        K --> L{governance context?}
        L -->|No| M[RuntimeError]
    end
```



---

## Fix 1: Duplicate Tool Registration

**Root Cause:** `memory_write` is registered twice:

- In [runtime/l_tools.py](runtime/l_tools.py) line 107 via `@register_tool` decorator
- In [core/tools/memory_tools.py](core/tools/memory_tools.py) line 405-407 via executor mapping

**Fix:** Remove the `@register_tool` decorator from `runtime/l_tools.py` for `memory_write`, similar to the fix already applied for `memory_search`.

**File:** `runtime/l_tools.py`

```python
# Line 107 - REMOVE this decorator:
@register_tool(category="memory", priority=10, description="memory_write tool")

# Add comment like memory_search:
# Note: memory_write is registered in core/tools/memory_tools.py
```

---

## Fix 2: Neo4j Connection (GMP-132 - ALREADY DONE LOCALLY)

**Root Cause (from GMP-132):** Server was calling `get_neo4j_client()` which only retrieves an existing singleton - it does NOT create one. Should use `init_neo4j_client()`.

**Fix Applied Locally (uncommitted):**

- [api/server.py](api/server.py) - Changed `get_neo4j_client()` to `init_neo4j_client()`
- [memory/graph_client.py](memory/graph_client.py) - Added diagnostic logging

**Action Required:** Commit and push the existing changes:

```bash
git add api/server.py memory/graph_client.py reports/GMP-Report-132-Neo4j-Unavailable-Fix.md
git commit -m "fix(neo4j): use init_neo4j_client instead of get_neo4j_client (GMP-132)"
git push origin main
```

---

## Fix 3: World Model Governance Context

**Root Cause:** `WorldModelRuntime.run_forever()` calls `substrate_service.query_packets()` which requires governance context. The RLS scope is set on `MemorySubstratePacketSource`, but the `substrate_service` method requires a governance context in the ContextVar.

**Error location:** [memory/governance_gate.py](memory/governance_gate.py) line 242-249

```python
def require_governance_context(operation: str) -> MemoryGovernanceContext:
    ctx = _governance_context.get()
    if ctx is None:
        raise RuntimeError(f"Governance context required for memory operation: {operation}")
```

**Fix in [world_model/runtime.py](world_model/runtime.py):**

Wrap `fetch_packets` call with governance context using existing pattern from [memory/slack_ingest.py](memory/slack_ingest.py) lines 216-228:

```python
# In MemorySubstratePacketSource.fetch_packets() around line 243:
async def fetch_packets(self, ...):
    if not self.substrate_service:
        return []
    
    try:
        self._ensure_scope(self.tenant_id, self.org_id, self.user_id)
        
        # ADD: Wrap with governance context
        from memory.governance_gate import build_governance_context, governance_context
        
        gov_ctx = build_governance_context(
            caller_id="world_model_runtime",
            role="system",
            scope="agent",
            project_id=os.getenv("L9_PROJECT_ID", "l9"),
            allowed_scopes=["agent", "memory", "global"],
            tenant_id=self.tenant_id,
            org_id=self.org_id,
            user_id=self.user_id,
            creator="world_model",
            source="runtime_fetch",
        )
        
        async with governance_context(gov_ctx):
            result = await self.substrate_service.query_packets(...)
```

---

## Fix 4: Seed Loader Governance Context

**Root Cause:** Same as Fix 3 - `write_packet` requires governance context.

**Fix in [world_model/seed_loader.py](world_model/seed_loader.py):**

Wrap `write_packet_to_substrate()` with governance context:

```python
# In write_packet_to_substrate() around line 202:
async def write_packet_to_substrate(self, packet: PacketEnvelope) -> bool:
    try:
        from memory.governance_gate import build_governance_context, governance_context
        from config.rls_config import get_rls_config
        
        rls_config = get_rls_config()
        gov_ctx = build_governance_context(
            caller_id="seed_loader",
            role="system",
            scope="agent",
            project_id=os.getenv("L9_PROJECT_ID", "l9"),
            allowed_scopes=["agent", "memory", "global"],
            tenant_id=rls_config.tenant_uuid,
            org_id=rls_config.org_uuid,
            user_id=rls_config.user_uuid,
            creator="seed_loader",
            source="write_packet",
        )
        
        async with governance_context(gov_ctx):
            # existing write_packet logic
```

---

## Execution Order

1. **Fix 1 (duplicate tools)** - Simple, unblocks tool graph
2. **Fix 2 (Neo4j)** - Requires investigation first, unblocks 5 features
3. **Fixes 3+4 (governance)** - Can be done together, unblocks background processing

## Verification

After each fix:

```bash
# Rebuild and restart
ssh c1 "cd /opt/l9 && git pull && \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml build l9-api && \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps l9-api"

# Check logs
ssh c1 "docker logs l9-l9-api-1 2>&1 | grep -E 'error|ERROR|failed|Neo4j|Governance' | tail -20"

# Health check
ssh c1 "curl -s http://127.0.0.1:8000/health"
```

## Success Criteria

- No "DuplicateRegistrationError" in logs
- "Neo4j connected" or successful graph operations
- No "Governance context required" errors
- World Model runtime processes packets without errors
- All 8 containers healthy

