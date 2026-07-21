---
description: "AI-to-AI Handoff Document: Graphiti Memory Subsystem & Zep Cloud Migration"
author: "L9 Systems Analyst"
date: "2026-07-04"
target_agent: "Next Execution Agent (Claude/Cursor)"
context_scope: "Graphiti Memory Integration"
---

# L9 Graphiti Handoff Pack

## 1. Core Knowledge Base & System State

**Current Architecture:**
The L9 architecture uses a bi-temporal knowledge graph to solve LLM "stochastic amnesia." The system intercepts IDE actions (Shell, Write, Tool use) via bash hooks (`ops/hooks/graphiti-*.sh`), forces a "search-before-write" discipline, and extracts temporal episodes (lessons, ADRs) into a persistent graph using `ops/graphiti/graphiti_memory_client.py`.

**Current Broken State:**
The self-hosted Hetzner C1 VPS deployment (`46.62.243.82`) is **BROKEN**. It returns HTTP 200 for `/healthcheck` but HTTP 404 for `/mcp/`. All reads/writes currently fail.

**Strategic Decision (LOCKED):**
We are **ABANDONING** the self-hosted Hetzner C1 deployment. The flawless victory path is migrating the memory layer to **Zep Cloud (Managed Graphiti)**. Zep Cloud is the official managed service built by the Graphiti team (`getzep`), offering the exact same temporal graph architecture without the DevOps maintenance burden.

## 2. Reasoning Framework & Next Execution Directives

**The Directive:**
The next agent must execute the migration from the local HTTP MCP client to the Zep Cloud SDK/MCP bridge.

**What Must NOT Change:**
- The Gate logic (`graphiti_gate_lib.py`) remains identical. The rules for blocking destructive actions based on memory prefetch are sacred.
- The `episode_contract.py` schema remains identical.
- The bash hooks (`ops/hooks/`) remain identical (they just call the Python client).
- The `group_resolver.py` logic remains identical.

**What MUST Change:**
- `graphiti_memory_client.py` must be refactored to use the `zep-python` SDK or a Composio MCP URL instead of `urllib` calls to `127.0.0.1:8100/mcp`.
- `ensure_graphiti_tunnel.sh` must be archived/deleted.
- The `docker-compose.yml` Graphiti section must be archived/deleted.

## 3. Implementation Constraints & Rules

1.  **No VPS Debugging:** Do not attempt to fix the 404 error on the Hetzner server. That path is deprecated.
2.  **Authentication:** The new client must expect a `ZEP_API_KEY` (or `GRAPHITI_MCP_TOKEN` mapped to Zep) loaded via the existing `graphiti_env_loader.py` Keychain mechanism. Do not hardcode keys.
3.  **Validation:** The migration is only successful when `test_gate_e2e_full.sh` passes using the Zep Cloud backend.
4.  **No Placeholders:** Do not write stub functions. If integrating the Zep SDK, write the full, production-ready integration.

## 4. DORA Block v2.0 (Target State)

```json
{
  "block_id": "GMP-L.2-graphiti-zep-migration-2026-07-04",
  "task_type": "infrastructure_migration",
  "status": "pending_execution",
  "target_files": [
    "ops/graphiti/graphiti_memory_client.py",
    "ops/hooks/ensure_graphiti_tunnel.sh"
  ],
  "success_criteria": [
    "Client successfully connects to api.getzep.com",
    "search_facts returns valid data from Zep Cloud",
    "add_episode successfully writes to Zep Cloud",
    "test_gate_e2e_full.sh passes"
  ],
  "rollback_plan": "git checkout main (reverts to Hetzner HTTP client)"
}
```

## 5. Execution Handoff Command

**To the receiving agent:**
> "Acknowledge receipt of the L9 Graphiti Handoff Pack. Your task is to execute the Zep Cloud migration defined in Section 2. Begin by inspecting `ops/graphiti/graphiti_memory_client.py` and planning the SDK swap. Do not touch the VPS."
