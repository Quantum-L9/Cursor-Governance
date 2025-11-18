---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-RSN-001"
component_name: "n8n Agent Reasoning Profile"
layer: "intelligence"
domain: "reasoning"
type: "reasoning_profile"
status: "active"
created: "2025-10-10T04:30:00Z"
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
integrates_with: ["INT-RSN-002", "INT-RSN-003", "EXE-WF-001"]
api_endpoints: []
data_sources: [".cursor-commands/profiles/orchestrator.md"]
outputs: ["reasoning_decisions", "workflow_plans", "tool_selections"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Enable advanced reasoning for n8n workflow development, debugging, and automation"
summary: "Cursor-native technical operations and n8n agent reasoning framework for evaluating tools, building workflows, and generating maintainable automation decisions"
business_value: "Accelerates n8n workflow development with structured reasoning and tool-aware decision making"
success_metrics: ["workflow_quality_score >= 0.85", "reasoning_accuracy >= 0.90", "tool_selection_optimality >= 0.95"]

# === INTEGRATION METADATA ===
suite_2_origin: "reasoning_n8n.md v2.2.0"
migration_notes: "Enhanced with Suite 6 structure, MCP tool selection protocol, and comprehensive n8n-specific reasoning patterns"

# === TAGS & CLASSIFICATION ===
tags: ["reasoning", "n8n", "workflow", "automation", "tool_selection", "ynp_enabled"]
keywords: ["reasoning", "n8n", "workflow", "agent", "automation", "tool_selection", "mcp"]
related_components: ["INT-RSN-002", "INT-RSN-003", "INT-ORC-001", "EXE-WF-001"]
startup_required: true
mode_type: "reasoning"
---

# n8n Agent Reasoning — Governance Brain

## 🛠️ Cursor-Native Technical Operations & n8n Agent Reasoning Framework v2.2

A unified reasoning block for use in Cursor.
Optimized for evaluating tools, building and debugging n8n agents, analyzing technical systems, and generating maintainable automation decisions from within the actual codebase.

---

## ⚙️ MODE: cursor_technical_reasoning

**Agent subtype:** n8n, tool_selection, api_integration, or infra_eval

**When to use:** ANY n8n-related task including:
- Building n8n agents
- Debugging n8n workflows
- Evaluating n8n nodes
- Analyzing n8n automations
- Selecting tools for n8n projects
- Integrating APIs with n8n

---

## 🧭 Structured Reasoning Flow

### 1️⃣ DEFINE THE TECHNICAL OBJECTIVE

**What task, automation, or architectural problem are you solving?**

- What is the intended input and expected output?
- What trigger or condition initiates this process (e.g., schedule, webhook, user)?
- What level of reliability, scale, or runtime control is needed?
- Who is the user or consumer of the output?

> 🎯 *Be specific. n8n workflows and ops choices require clear I/O definition.*

---

### 2️⃣ HYDRATE THE WORKSPACE CONTEXT (Cursor-Specific)

**Use Cursor's tools to scan, locate, and load key project elements:**

- `list_dir()` → Understand top-level structure
- `grep("n8n")`, `grep("workflow")`, `grep("auth")`, `grep("API")`
- `read_file()` →
  - Load any `.n8n.json` agent definitions
  - Open helper functions or `.env` configurations
  - Inspect prior integrations (e.g., `lib/`, `services/`, `api/`)

**Check for:**
- `package.json`, `Dockerfile`, `infra/`, `nodes/`, `workflows/`, `docs/`, `.env`

**For n8n projects - Check available MCP tools:**
- **n8n-mcp**: Direct instance management (create, update, validate workflows)
- **n8n-workflows Docs MCP**: 2,057 workflow examples and documentation
- **Context7**: n8n library documentation lookup
- **firecrawl_extract** (NOT scrape!): For extracting structured n8n docs from web

> 💧 *Never reason blindly. The truth is in the codebase and the tools available.*

---

### 3️⃣ BREAK DOWN THE TECHNICAL COMPONENTS

**Identify the parts of the task:**
- Data fetching
- Transformation
- Auth
- Conditionals
- API interaction
- Persistence

**For n8n agents:**
- Trigger node?
- How many nodes, and what type?
- Are there loops, switches, or function nodes?
- What services or data sources are involved?
- What errors, side effects, or constraints should be anticipated?

> 🧩 *Break the flow into traceable logic segments.*

---

### 4️⃣ EVALUATE DESIGN STRATEGY & TOOL FIT

**Choose the right framework for each part:**

#### ✅ For n8n agents:

**Use the n8n Agent Creation Checklist:**
- Is the workflow stateless or does it persist across steps?
- Are inputs validated or assumed?
- Are credentials handled securely?
- Could custom JS or templates reduce complexity?
- Are retry/fallback paths defined?

#### ✅ For tech/tool selection:

**Tool fit:**
- Ecosystem
- Maintenance
- Modularity

**Integration risk:**
- Does it conflict with existing stack?

**Efficiency:**
- Can it replace manual work or legacy code?

**Use:**
- Tool Selection Protocol
- API Evaluation Protocol
- Technology Fit Matrix
- **MCP Tool Selection Protocol** (see section below)

> 🧠 *Good reasoning matches the right tech to the real constraint.*

---

### 5️⃣ EXECUTE TECHNICAL ANALYSIS (WITH CURSOR TOOLS)

**Use Cursor's commands:**

- `grep()` → Trace how services or APIs are called
- `read_file()` → Check node configs, credentials, headers, timeouts
- **Inspect node JSON (n8n):** check inputs/outputs, error nodes, or missed joins
- **Simulate payloads** (for webhooks, APIs) and predict execution path
- **Test function nodes:** are return values formatted correctly?
- **Scan for:** missing error handling, infinite loops, or race conditions

> 🧪 *Debug agents like systems: state, flow, side effects.*

---

### 6️⃣ SYNTHESIZE THE RECOMMENDATION OR AGENT PLAN

**Summarize the best path forward:**
- Tool choice
- Workflow shape
- Error and retry handling
- Observability

**Provide:**
- ✅ Summary decision (1–2 sentences)
- ✅ Confidence score (1–10)
- ✅ Trade-offs noted clearly
- ✅ Recommend specific files to create or update

> 🧵 *Synthesis turns insights into ship-ready plans.*

---

### 7️⃣ VALIDATE AGAINST EDGE CASES

**Does the automation handle:**
- Missing input?
- Downstream API failure?
- Rate limits or timeouts?
- Are webhook or schedule triggers debounce-safe?
- Could a restart or partial failure cause duplication or data loss?
- Will this decision age well?

> 🧪 *Stress tests make automation production-safe.*

---

### 8️⃣ PLAN CODEBASE ACTIONS

**What should be scaffolded?**
- `workflows/new-agent.n8n.json`
- `/nodes/helpers/*.js`
- `.env.example` updates
- `docs/agent_overview.md`

**Can any of these be auto-generated?**

**Should a PR or ADR be created?**

> 📄 *Great decisions generate trackable changes.*

---

### 9️⃣ IDENTIFY AUTOMATION RISKS

**Consider:**
- External dependency health (API stability, auth, rate limits)
- Credential storage or expiration issues
- Missing logging, observability, or version control
- High-latency steps that may bottleneck flows
- Loops or concurrency errors in n8n logic
- **Is this agent idempotent?**

> ⚠️ *Think like SRE: what breaks at 2AM?*

---

### 🔟 TEAM FIT & MAINTAINABILITY

**Questions:**
- Is this aligned with how other agents are built?
- Can another engineer troubleshoot it easily?
- Will this need ongoing support, monitoring, or cleanup?
- Does it introduce new patterns that must be documented?

> 👥 *The best tech choices are those the team can live with later.*

---

## ✅ SUPPORTED ATTACHMENTS & PROTOCOLS

### 🔌 MCP Tool Selection Protocol (CRITICAL)

**BEFORE using ANY MCP tool for n8n work:**

1. **List ALL available tools**
   ```
   Available n8n-related MCPs:
   - n8n-mcp (instance management)
   - n8n-workflows Docs (2,057 examples)
   - Context7 (library docs)
   - firecrawl (web scraping/extraction)
   ```

2. **Compare capabilities**
   | Tool | Output | Best For | When to Use |
   |------|--------|----------|-------------|
   | n8n-mcp | Direct API | Create/manage workflows | Working with YOUR instance |
   | n8n-workflows Docs | Examples | Learning patterns | Finding workflow examples |
   | Context7 | Documentation | Node reference | Looking up node docs |
   | firecrawl_extract | Structured JSON | Building KB | Extracting structured data |
   | firecrawl_scrape | Markdown | Reading docs | Quick doc viewing |

3. **Match to objective**
   - Need to create workflow? → n8n-mcp
   - Need workflow examples? → n8n-workflows Docs
   - Need node documentation? → Context7 or firecrawl_extract
   - Need to validate workflow? → n8n-mcp validate tools

4. **Validate against context**
   - Check what's already being used in codebase
   - Verify API keys are configured
   - Ensure tool supports needed features

5. **Execute with reasoning**
   - Document why you chose this specific tool
   - Note alternatives considered
   - Explain trade-offs

**Example:**
```
Task: Build comprehensive n8n node documentation

Step 1 - List:
✓ firecrawl_scrape (returns markdown)
✓ firecrawl_extract (returns structured JSON) ← BEST
✓ n8n-mcp (direct API, not for docs)
✓ Context7 (library lookup, not comprehensive)

Step 2 - Compare:
extract: Structured JSON with custom schema ✅
scrape: Unstructured markdown text
n8n-mcp: For instance management, not docs
Context7: Good for lookups, not bulk extraction

Step 3 - Match:
Objective: Structured, queryable KB
Best tool: firecrawl_extract with schema

Step 4 - Validate:
✅ API key configured
✅ Schema capability available
✅ Can handle 500+ pages

Step 5 - Execute:
Using firecrawl_extract to build structured n8n docs
Reasoning: Returns JSON, supports schema, queryable
```

---

### 🧠 n8n Agent Creation Checklist

- ✅ Trigger clearly defined?
- ✅ Inputs mapped and validated?
- ✅ External services integrated with retries?
- ✅ Fallbacks and alerts in place?
- ✅ Uses reusable JS nodes if needed?
- ✅ Monitored or logged?
- ✅ Failures recoverable or at least visible?

---

### 🔬 n8n Agent Debugging Protocol

1. **Inspect execution logs** (via n8n UI or rawData)
2. **Reproduce with known inputs**
3. **Isolate failure node**
4. **Check data paths, credentials, and return structures**
5. **Confirm: input/output structure at each step**
6. **Debug function nodes for `return [{ json }]` compliance**

---

### 🔧 Tool/API Evaluation Protocol

**Evaluate:**
- Documentation
- Auth
- Test sandbox
- Community

**Check:**
- Rate limits
- Retries
- Response time
- Pagination

**Validate:**
- Versioning stability
- Error handling behavior

**Scan for:**
- Similar usage in repo

---

## 🧠 Final Advice

> **Reason with the codebase, not just in abstract.**
> **Use the tools Cursor gives you — inspect, grep, and trace before you decide.**
> **Every agent is a system. Design it like one.**

---

## 🔗 Integration with Governance Suite

This profile integrates with:
- `orchestrator.md` — for n8n-specific task delegation
- `reasoning_docs.md` — for strategic document analysis when needed
- `reasoning_technical_operations.md` — for general tech decisions
- `workflow-governance.md` — for n8n workflow validation

**Priority:** When working on n8n-related tasks, this profile takes precedence over `reasoning_technical_operations.md`

**Behavior:** Autonomous • n8n-Aware • Tool-Explicit • YNP Enabled

---

## 🎯 When to Use This Profile

**ALWAYS use this profile for:**
- ✅ Building n8n workflows
- ✅ Debugging n8n agents
- ✅ Evaluating n8n nodes
- ✅ Analyzing n8n automations
- ✅ Selecting tools for n8n projects
- ✅ Integrating APIs with n8n
- ✅ Creating n8n documentation
- ✅ Validating n8n configurations

**Use `reasoning_technical_operations.md` for:**
- General infrastructure decisions
- Non-n8n tool selections
- System architecture choices

---

**Last Updated:** 2025-10-10T04:30:00Z  
**Status:** Active ✅  
**Scope:** n8n-specific operations and agent development

