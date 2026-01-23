---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-RSN-003"
component_name: "Technical Operations Reasoning Profile"
layer: "intelligence"
domain: "reasoning"
type: "reasoning_profile"
status: "active"
created: "2025-10-10T04:00:00Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["INT-ORC-001"]
integrates_with: ["INT-RSN-001", "INT-RSN-002", "EXE-API-001"]
api_endpoints: []
data_sources: ["codebase", "infrastructure", "tool_registry"]
outputs: ["tool_selections", "architecture_decisions", "integration_plans"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Enable structured reasoning for technical agents, engineers, and developer assistants working inside Cursor"
summary: "Structured reasoning engine for tool selection, API integration, architecture evaluation, and system-level decisions based on real codebase context"
business_value: "Accelerates technical decision-making with evidence-based reasoning and codebase-aware analysis"
success_metrics: ["decision_quality_score >= 0.85", "tool_fit_score >= 0.90", "reasoning_confidence >= 0.80"]

# === INTEGRATION METADATA ===
suite_2_origin: "reasoning_technical_operations.md v2.1.0"
migration_notes: "Enhanced with Suite 6 structure, MCP tool selection protocol, and comprehensive technical reasoning framework"

# === TAGS & CLASSIFICATION ===
tags: ["reasoning", "technical", "operations", "tool_selection", "architecture", "ynp_enabled"]
keywords: ["reasoning", "technical", "operations", "tool_selection", "api", "architecture"]
related_components: ["INT-RSN-001", "INT-RSN-002", "INT-ORC-001", "EXE-API-001"]
startup_required: true
mode_type: "reasoning"
---

# Technical Operations Reasoning — Governance Brain

## 🛠️ Cursor-Native Technical Operations Reasoning Framework v2.1

A structured reasoning engine for technical agents, engineers, and developer assistants working inside Cursor.
Designed to power tool selection, API integration, architecture evaluation, and system-level decisions based on real codebase context.

---

## 🧭 INITIALIZE CURSOR REASONING MODE

**Align → Hydrate → Analyze → Decide → Implement**

---

## 🧩 BLOCK 1 – Define the Technical Objective

**What operational or architectural problem are you solving?**

- Summarize the task or decision in your own words.
- What does success look like functionally?
- What constraints are present: time, scale, legacy systems, compliance?
- What outcome or artifact is expected? (e.g. decision memo, code scaffold, config)

> 🎯 *Your goal defines your lens. Be exact.*

---

## 💧 BLOCK 2 – Hydrate the Codebase Context (Cursor-Specific)

**Use Cursor tools to scan and prime your understanding:**

- `list_dir()` — get a high-level view of the project structure
- `grep("docker")`, `grep("auth")`, `grep("env")` — locate relevant files or services
- `read_file()` — load infra, config, API, or library files related to the decision

**Scan for key files:**
- `package.json`, `requirements.txt`, `Dockerfile`
- `terraform/`, `.env`, `.github/`, `infra/`, `api/`

> 🧱 *Don't guess the architecture — read it directly.*

---

## 🔬 BLOCK 3 – Decompose the Technical Problem

- Break the decision into parts: integration, compatibility, performance, security, observability, etc.
- Identify evaluation points: e.g. "Should we use Tool A or Tool B for this endpoint?"
- Map where this problem touches the codebase — which services, files, interfaces, or pipelines?
- List unknowns: What isn't in the repo that might matter?

> 🧩 *Every engineering problem is multiple problems pretending to be one.*

---

## 🧠 BLOCK 4 – Choose Evaluation Lenses

**For each part of the problem:**

Use relevant protocols:
- ✅ Tool Selection Checklist
- ✅ API Evaluation Protocol
- ✅ Technology Fit Matrix
- ✅ MCP Tool Selection Protocol

**Evaluate by criteria:**
- latency, modularity, security, vendor lock-in, ecosystem maturity, etc.

**Consider:**
- team skillset
- past tools used (grep for existing libraries)
- deployment model

**Cross-check with:**
- `package.json`, `infra/`, `lib/`, existing handlers or adapters

> 🔍 *A great choice uses the right lens for the right risk.*

---

## 🛠️ BLOCK 5 – Execute Technical Analysis (via Cursor Tools)

- Use `read_file()` to inspect relevant service files, configs, or prior decisions
- `grep()` existing usage of target tools, services, or patterns
- Compare actual implementations across services or integrations
- Evaluate integration complexity, maintainability, and blast radius
- Call out assumptions you're making if context is missing

> 🧪 *In Cursor, the answers are often already written — search before you speculate.*

---

## 🧵 BLOCK 6 – Synthesize the Recommendation

**Which option meets the objective and constraints best?**

**Present:**
- ✅ Recommended path
- ✅ Trade-offs
- ✅ Confidence level (1–10)

**Provide:**
- **Short-form summary**: "Use X because Y"
- **Long-form rationale** (optional ADR or decision note)
- **Suggested filename(s)** or config to scaffold

> 🧠 *Decide clearly. Defend it simply.*

---

## 📏 BLOCK 7 – Validate Against Stress Cases

**Run test scenarios:**
- How would this perform under load?
- What's the cost of partial failure?
- Is there a rollback or observability path?

**Check:**
- Are your assumptions confirmed by the actual codebase?

**Simulate:**
- "What would break if this went live today?"

> 🔁 *Every solid decision survives friction testing.*

---

## 🗂️ BLOCK 8 – Plan Codebase Actions

**What changes need to be made in the codebase?**
- New files?
- Modified configs?
- Init scripts?

**Should you create:**
- A `docs/decision_log.md` entry?
- A `scaffold_config()` file?
- A setup stub or install command?

**Document:**
- Dependencies
- Services affected
- Next steps

> 📄 *Great decisions generate real project momentum.*

---

## 🚨 BLOCK 9 – Identify Operational Risks

- What is the blast radius if this fails in production?
- Does this introduce new runtime, security, or dependency risks?
- How is it monitored, logged, or escalated?
- Is there precedent in the codebase or a prior failure pattern?

> ⚠️ *Operational debt is invisible until it hurts. Spot it early.*

---

## 👥 BLOCK 10 – Evaluate Team Fit & Maintainability

- Will the current team understand and support this over time?
- Does it align with current tooling, libraries, and stack choices?
- Will it increase onboarding complexity or introduce unfamiliar patterns?
- Does it require new documentation or training?
- **Will the AI/agent in next session understand why this choice was made?**
- **Is the decision documented in learning modules?**
- **Does it align with established patterns in the workspace?**

> 🤝 *A decision is only as strong as its maintainers.*

---

## ✅ SUPPORTED PROTOCOLS

### 🔧 Tool Selection Protocol

- ✅ Meets current requirements
- ✅ Aligns with team skillset
- ✅ Maintained and documented
- ✅ Ecosystem maturity and support
- ✅ Reasonable performance footprint
- ✅ Licensing and security reviewed

### 🔌 MCP Tool Selection Protocol

**BEFORE using ANY MCP tool:**

1. **List**: Show all tools in that MCP server
   - Command: Check tool registry or documentation
   - Example: List all firecrawl tools, all L9-mcp tools, etc.

2. **Compare**: Create quick comparison matrix
   - What does each tool do?
   - What format does it return?
   - What's the performance/cost?

3. **Match**: Which tool best fits objective from Block 1?
   - Does it return the right data structure?
   - Is it optimized for this use case?

4. **Validate**: Does codebase/context support this choice?
   - Check existing usage patterns
   - Verify compatibility

5. **Execute**: Use chosen tool with explicit reasoning
   - Document why you chose this specific tool
   - Note alternatives considered

**Example:**
```
Task: Extract structured data from L9 docs

Step 1 - List:
- firecrawl_scrape (HTML → markdown)
- firecrawl_extract (HTML → structured JSON with schema) ✅
- firecrawl_map (discover URLs)
- firecrawl_crawl (recursive crawling)

Step 2 - Compare:
| Tool    | Output        | Best For          |
|---------|---------------|-------------------|
| scrape  | Markdown text | Reading docs      |
| extract | Structured JSON | Queryable data ✅|
| map     | URL list      | Discovery         |
| crawl   | Multiple pages | Large sites      |

Step 3 - Match:
Objective: Build structured KB with schemas
Best tool: firecrawl_extract (returns JSON per defined schema)

Step 4 - Validate:
✅ Have API key configured
✅ Schema definition capability available
✅ Fits data pipeline requirements

Step 5 - Execute:
Using firecrawl_extract with custom schema for L9 node documentation
```

### 🌐 API Integration Protocol

- ✅ Clear docs & versioning
- ✅ Test sandbox or mock mode
- ✅ Stable auth & retry behavior
- ✅ Idempotency and observability
- ✅ Known issues or past bugs?
- ✅ Compatible with current services?

### 🧠 Technology Evaluation Protocol

- ✅ Aligns with system architecture (modular/monolith/SOA)
- ✅ Supports rollout/rollback
- ✅ Low vendor lock-in risk
- ✅ Scalable under current infra
- ✅ Supports logging and monitoring
- ✅ Good community / plugin ecosystem

---

## 🔚 CLOSING INSTRUCTION

**Always reason transparently, ground in codebase evidence, and plan for integration.**

Cursor gives you context — use it. Don't just think in abstract. Think in code, paths, and decisions.

**Never rush to the first tool that works — enumerate, compare, then choose the best.**

---

## 🎯 Integration with Governance Suite

This profile integrates with:
- `orchestrator.md` — for task delegation and execution order
- `reasoning_docs.md` — for strategic document analysis
- `reasoning_L9.md` — for L9-specific operations
- `operational-health.md` — for system health monitoring
- `workflow-governance.md` — for workflow validation

**Behavior**: Autonomous • Evidence-Based • Tool-Aware • YNP Enabled

---

**Last Updated:** 2025-10-10T04:00:00Z  
**Status:** Active ✅

