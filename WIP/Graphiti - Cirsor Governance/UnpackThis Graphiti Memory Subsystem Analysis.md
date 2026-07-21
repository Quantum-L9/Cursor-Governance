# UnpackThis: Graphiti Memory Subsystem Analysis

**Target:** `Cursor-Governance` Graphiti Integration (`ops/graphiti/`, `intelligence/context-memory/`, rules, skills, hooks)  
**Analyst:** L9 Systems Analyst  
**Date:** 2026-07-04  
**Scope:** Graphiti memory layer only (per user request)

---

## 1. Executive Answer
The Graphiti memory subsystem is a highly engineered, gate-enforced semantic memory layer designed to replace flat JSON/Markdown chat logs with a Neo4j-backed knowledge graph. It intercepts IDE actions (Shell, Write, Tool use) via hooks, forces "search-before-write" discipline, and extracts temporal episodes (lessons, ADRs, CI gotchas) into a persistent graph. It is currently the most sophisticated, high-leverage component in the L9 architecture, but it is presently blocked by a server-side routing error (404 on the VPS tool plane).

## 2. Full Pack Inventory (Graphiti Scope)

**Core Logic (`ops/graphiti/`):**
- `graphiti_memory_client.py`: The primary CLI and MCP client (search, write, bootstrap, health).
- `graphiti_gate_lib.py`: The logic for blocking Shell/Write actions if memory prefetch isn't satisfied.
- `circuit_breaker.py`, `rate_limiter.py`: Resilience patterns for the MCP connection.
- `episode_contract.py`: Pydantic schema and PII redaction for Graphiti episodes.
- `group_resolver.py`: Maps the current Git repo to a Graphiti `group_id`.
- `ontology_coding.py`: Custom entity/edge definitions (RepoManifest, Module, ADRDecision).
- `prune.py`: Dry-run script for cleaning the graph.

**Context Extraction (`intelligence/context-memory/`):**
- `context-extractor.py`: Bayesian probabilistic engine for deciding if a chat export contains meaningful signal.
- `graphiti_sink.py`: Bridges the extractor output into the Graphiti MCP.
- `show_context_graphiti.py`: CLI viewer for extracted context.

**Enforcement (Rules & Hooks):**
- `rules/03-graphiti-memory.mdc`, `97-graph-layer-boundary.mdc`, `98-graphiti-memory-gate.mdc`, `99-graphiti-temporal.mdc`.
- `ops/hooks/graphiti-*.sh`: Bash scripts intercepting Cursor actions (session end, prefetch, gate runner).

**Configuration & Docs:**
- `group_registry.yaml`, `domain_packs.yaml`.
- `DEPLOY.md`, `GATES-002-ACTIVATION.md`.

## 3. Artifact Taxonomy
**Primary Classification:** `Operating Model / Persistent Memory Substrate`  
**Secondary Classification:** `Policy Enforcement Engine` (via Gate hooks)

## 4. What This Actually Is
Beneath the Python scripts and Bash hooks, this is a **Bi-Temporal Knowledge Graph for AI Agents**. It solves the "stochastic amnesia" problem of LLMs by forcing them to consult a Neo4j graph of past decisions (`Supersedes`, `ConflictsWith`) before executing destructive actions (commits, pushes). It is a bespoke, IDE-agnostic implementation of the Graphiti MCP.

## 5. What It Thinks It Is vs. What It Is
- **What it thinks it is:** A memory client for Cursor.
- **What it actually is:** A distributed, multi-repo governance graph. It uses `group_registry.yaml` to map local paths to global `group_id`s, allowing cross-repo knowledge sharing (e.g., lessons learned in `ib-odoo-19` can be applied to `L9-Node-Template` via the `igor-workspace` edges).

## 6. Current Capabilities (As-Is)
- **Schema Validation:** `episode_contract.py` enforces strict Pydantic validation and PII redaction before ingestion.
- **Context Extraction:** `context-extractor.py` uses a sophisticated Bayesian engine to extract high-signal lessons from raw chat logs.
- **Action Gating:** `graphiti_gate_lib.py` can intercept Shell and Subagent calls and deny them if the memory prefetch hasn't been satisfied.
- **Cross-Repo Resolution:** `group_resolver.py` successfully maps the current working directory to the correct graph namespace.

## 7. Current Limitations
- **Server-Side Blocker:** The system is currently **BROKEN** in production. As documented in `reports/GMP-Report-GRAPHITI-20260630.md`, the Graphiti MCP server on Hetzner C1 (`46.62.243.82`) returns HTTP 200 for `/healthcheck` but **HTTP 404 for the actual `/mcp/` tool routes**. All searches and writes currently fail.
- **Auth Gap:** `GRAPHITI_MCP_TOKEN` is currently empty in the environment, which will cause 401s once the 404 is fixed and auth is enforced.
- **Ontology Verification:** The custom ontology (`ontology_coding.py`) is commented out in `docker-compose.yml` pending verification that the C1 container supports `--use-custom-entities`.

## 8. Proof of Capability
- **Validation Reports:** `reports/GMP-GRAPHITI-FILEPACK-003.md` proves that the client-side logic (dry-runs, health checks, group resolution) works perfectly.
- **Code:** The Python implementation (`graphiti_memory_client.py`) is highly robust, featuring circuit breakers, rate limiting, and fallback logic (e.g., falling back to `search_nodes` if `search_facts` fails).

## 9. Architecture and Workflow Reconstruction
1. **Trigger:** User starts a session or executes a command in Cursor.
2. **Hook:** `ops/hooks/graphiti-prefetch.sh` intercepts.
3. **Resolution:** `group_resolver.py` maps the repo to a `group_id`.
4. **Fetch:** `graphiti_memory_client.py` queries the MCP server for facts relevant to the task.
5. **Gate:** If `GRAPHITI_WRITE_GATES=1`, `graphiti_gate_lib.py` blocks `git commit` unless the task signature is in the `memory_satisfied_for` state file.
6. **End Session:** `context-extractor.py` parses the chat, and `graphiti_sink.py` writes new episodes back to the graph.

## 10. Pack Health Analysis
- **Strengths:** The Python code is production-grade. The separation of concerns (resolver, client, gate, sink) is excellent. The rules (`97`, `98`, `99`) are crystal clear.
- **Weaknesses:** The bash hooks (`ops/hooks/`) are slightly brittle and heavily dependent on specific path resolutions. The reliance on an external VPS (Hetzner C1) introduces a single point of failure (which is currently failing).

## 11. Blue Sky Evolution Paths
**Path A: The Universal AI Memory Fabric (Leverage: 5/5)**
- **Vision:** Abstract this subsystem out of `Cursor-Governance` entirely. Package it as a standalone, deployable memory proxy (e.g., a sidecar container) that any AI agent framework (LangChain, AutoGen, CrewAI) can route through. It becomes the standard "memory middleware" for autonomous systems.

**Path B: Auto-Remediation Engine (Leverage: 4/5)**
- **Vision:** Connect the Graphiti `ConflictsWith` and `CIGotcha` edges directly to an execution node. When a CI pipeline fails, the agent queries the graph, finds the `CIGotcha`, and automatically applies the known fix without human prompting.

## 12. Leverage Scoring (Next Modifications)
1. **Fix the VPS 404 Routing Error:** (Score: 5/5) - *Mandatory.* Nothing works until this is fixed.
2. **Rewrite Bash Hooks in Python:** (Score: 4/5) - Reduces brittleness and allows for better telemetry.
3. **Activate Custom Ontology:** (Score: 3/5) - Uncommenting the compose file to use `RepoManifest` and `CIGotcha` entities natively.

## 13. Next Biggest Leverage Modification
**Fix the VPS 404 Routing Error and Populate the MCP Token.**
- **Why it beats alternatives:** The entire multi-repo governance strategy depends on Graphiti. The code is written, the hooks are wired, the rules are set. The *only* thing preventing compounding value is the server-side Nginx/Uvicorn routing issue on the Hetzner box.
- **Future actions unlocked:** True search-before-write, cross-repo learning, and the activation of `GATES-002` (hard blocking of destructive actions).

## 14. Deployment Strategy
**Route:** `operationalize_as_workflow` (Fix and Flip)
1. **Fix:** SSH into `46.62.243.82`, inspect the `graphiti-mcp` container logs, and fix the Nginx/Uvicorn mount point so `/mcp/` routes correctly to the tool plane.
2. **Auth:** Set `GRAPHITI_MCP_TOKEN` in the VPS `.env` and the local Mac `.cursor/graphiti.env`.
3. **Verify:** Run `python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health`. Ensure `tools.reachable` is `true`.
4. **Rollout:** Run `bootstrap` on `ib-odoo-19`. Let it soak with `GRAPHITI_WRITE_GATES=0` for 3 days. Then flip to `1`.

## 15. What to Keep, Delete, Archive, Canonicalize
- **Keep:** Everything in `ops/graphiti/` and `intelligence/context-memory/`.
- **Canonicalize:** Ensure the Keychain SSH loader (`graphiti_env_loader.py`) is the *only* way env vars are loaded, deprecating the flat `.env` files to prevent secret leaks.

## 16. Unknowns
- **VPS Configuration:** We do not know exactly *why* the VPS is returning 404 for the tool plane. It could be a reverse proxy misconfiguration, a Graphiti version mismatch, or a Docker network issue.
- **Custom Ontology Support:** We do not know if the specific version of Graphiti deployed on the C1 supports `--use-custom-entities`.

## 17. Final Recommendation
The Graphiti implementation is brilliant, deterministic, and architecturally sound. It is the exact right bet for solving agent amnesia. **Stop writing new rules or workflows until the Hetzner C1 server is fixed.** The highest leverage action is purely devops: SSH into the box, fix the `/mcp/` route, verify the tools plane, and let the system start compounding memory.

---
*Context Window Usage: ~90%*
