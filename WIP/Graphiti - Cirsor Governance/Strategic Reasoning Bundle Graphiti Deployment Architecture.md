# Strategic Reasoning Bundle: Graphiti Deployment Architecture

**Target:** Graphiti Memory Subsystem Deployment Methodology
**Analyst:** L9 Systems Analyst
**Date:** 2026-07-04
**Kernels Applied:** `strategic_reasoning_flow`, `cognitive_pipeline_kernel`, `first_order_gate_system`, `flawless_victory_converged`

---

## 1. Cognitive Pipeline Analysis

### 1.1. Interpret & Retrieve (What do we know?)
The user wants to realize the "Flawless Victory" vision: abstracting the Graphiti memory subsystem into a standalone, deployable "memory middleware" for autonomous systems. The current deployment methodology relies on a self-hosted Docker Compose stack on a Hetzner C1 VPS (`46.62.243.82`). This setup is currently broken (404 on the `/mcp/` route) and represents a massive single point of failure (SPOF). The user explicitly prefers paying a premium for a managed service to offload maintenance and reduce the failure surface.

### 1.2. Analyze & Reason (What does the evidence say?)
Deep research into Graphiti and Neo4j hosting options reveals a critical structural reality: **Zep Cloud is the managed version of Graphiti.** The open-source `getzep/graphiti` framework (which the L9 architecture currently self-hosts) is built by the same team that operates Zep Cloud [1]. 

The options are:
1.  **Maintain Hetzner C1 (Self-Hosted):** Requires managing Neo4j, the Graphiti MCP server container, Nginx routing, SSL certificates, and SSH tunnels. It is brittle and currently failing.
2.  **Neo4j Aura + Self-Hosted MCP:** Offloads the database to Neo4j Aura (managed cloud) [2], but still requires hosting the Python MCP server somewhere (e.g., AWS Fargate, Render, or keeping the VPS). This only solves half the problem.
3.  **Zep Cloud (Fully Managed):** For $25/month, Zep provides the entire Graphiti infrastructure (graph storage, retrieval engine, embedding generation) as a fully managed service with SOC 2 Type II compliance [1]. Crucially, recent integrations (like Composio) demonstrate that Zep Cloud endpoints can be exposed directly as MCP servers [3].

### 1.3. Evaluate (Which path maximizes leverage?)
Self-hosting Graphiti violates the `flawless_victory_converged` contract's directive to "Deliver the strongest working result the repo evidence supports" by introducing unnecessary DevOps entropy. If the goal is a "Universal Memory Fabric," that fabric must be highly available. The Hetzner VPS is a distraction from building agent logic. 

## 2. First-Order Gate System Evaluation

### 2.1. Impact Gate
Does fixing the VPS materially advance the L9 architecture, or just restore baseline? It only restores baseline. Migrating to a managed service eliminates the class of errors (routing 404s, SSH tunnel drops) entirely.

### 2.2. Effort/Coverage Ratio
-   **Fixing VPS:** Low immediate effort (SSH and fix Nginx), but high ongoing maintenance tax.
-   **Migrating to Zep Cloud:** Medium immediate effort (refactoring `graphiti_memory_client.py` to use the Zep SDK or Composio MCP URL instead of the local HTTP MCP endpoint), but zero ongoing maintenance tax. The ROI is massively positive.

### 2.3. Rabbit Hole Detector
Attempting to debug Uvicorn ASGI mounts and Nginx reverse proxy configs on a remote Hetzner box is the definition of a DevOps rabbit hole. It does not compound the intelligence of the L9 agents.

## 3. Strategic Position & Execution Plan

### 3.1. The Decision
**ABANDON the Hetzner C1 VPS deployment methodology for the memory layer.** It is not the optimal path. The maintenance burden and failure surface directly contradict the goal of a highly reliable autonomous memory middleware. 

The optimal deployment methodology is **Zep Cloud (Managed Graphiti)**. 

### 3.2. Why Zep Cloud?
Zep Cloud is built on the exact same temporal knowledge graph architecture as the self-hosted Graphiti MCP [1]. It provides:
-   **Zero Infrastructure:** No Neo4j to manage, no Docker containers to restart.
-   **MCP Compatibility:** Can be connected to Cursor/Claude via Composio or direct SDK wrappers [3].
-   **Scale:** Sub-200ms retrieval and unlimited graph memories on the $25/mo Flex plan [1].

### 3.3. Execution Sequence (The "Flawless Victory" Path)

To execute this pivot without regressions, we must follow a strict sequence:

1.  **Provision:** Sign up for Zep Cloud and obtain an API key.
2.  **Adapter Refactor:** Modify `.cursor-commands/ops/graphiti/graphiti_memory_client.py`. Instead of making raw HTTP calls to `127.0.0.1:8100/mcp`, the client will use the official `zep-python` SDK to interact with the managed graph.
3.  **Gate Preservation:** The existing `graphiti_gate_lib.py` logic remains identical. The *decision* to block a commit based on memory state does not change; only the *transport* mechanism to fetch that state changes.
4.  **Deprecate VPS:** Once the Zep Cloud client passes the `test_gate_e2e_full.sh` suite, sever the SSH tunnel hooks (`ensure_graphiti_tunnel.sh`) and decommission the Hetzner containers.

## 4. Minimum Safe Next Action

Do not attempt to fix the Hetzner 404 error. Instead, **authorize the creation of a Zep Cloud account and the refactoring of `graphiti_memory_client.py` to use the Zep SDK.** This permanently eliminates the VPS failure surface.

---

## References
[1] Zep Pricing and Features. https://www.getzep.com/pricing/
[2] Neo4j Aura Cloud Pricing. https://neo4j.com/pricing/
[3] Composio: Zep MCP Integration with Claude Code. https://composio.dev/toolkits/zep/framework/claude-code
