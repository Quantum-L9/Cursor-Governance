---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-N8N-005"
component_name: "n8n MCP System Architecture"
layer: "intelligence"
domain: "n8n_automation"
type: "documentation"
status: "active"
created: "2025-01-27T00:00:00Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["INT-N8N-001"]
integrates_with: ["INT-N8N-002", "INT-N8N-003", "INT-N8N-004"]
api_endpoints: []
data_sources: ["n8n-mcp", "context7-mcp", "firecrawl-mcp"]
outputs: ["architecture_diagrams", "system_documentation"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: false
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Complete system architecture and setup documentation for n8n MCP workflow creation system"
summary: "Visual architecture diagrams, system overview, three-server integration patterns, and complete setup guide"
business_value: "Provides comprehensive understanding of system architecture for effective workflow creation"
success_metrics: ["system_understanding_score >= 0.90", "setup_success_rate >= 0.95"]

# === TAGS & CLASSIFICATION ===
tags: ["n8n", "architecture", "system-design", "mcp", "setup"]
keywords: ["n8n", "architecture", "system", "mcp", "setup", "diagrams"]
related_components: ["INT-N8N-001", "INT-N8N-002", "INT-N8N-003"]
startup_required: false
mode_type: "documentation"
---

# n8n MCP System Architecture

**Visual guide to your complete n8n workflow creation system**

**Status:** ✅ Production Ready | **Version:** 2.0 | **Last Updated:** 2025-01-27

---

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         YOUR CURSOR IDE                                 │
│                                                                         │
│  You write:                                                             │
│  "Create n8n workflow for BCP intelligence pipeline. use context7"   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE (Sonnet 4.5)                             │
│                    Running in Cursor                                    │
│                                                                         │
│  Receives your prompt, activates MCP servers based on:                 │
│  1. "n8n workflow" → Activates n8n-mcp                                 │
│  2. "use context7" → Activates Context7 MCP                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
         ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
         │  n8n-mcp     │ │  Context7   │ │  Firecrawl   │
         │   Server     │ │    MCP      │ │     MCP      │
         └──────────────┘ └─────────────┘ └──────────────┘
                │               │               │
                │               │               │
                ▼               ▼               ▼
    ┌──────────────────┐ ┌───────────────┐ ┌───────────────┐
    │ Your n8n Instance│ │ Upstash       │ │ Web Scraping  │
    │ ibeylin.app      │ │ Context7 API  │ │ Service       │
    │ n8n.cloud        │ │               │ │               │
    └──────────────────┘ └───────────────┘ └───────────────┘
```

---

## 🎯 What You Have Now

You have a **complete, production-ready n8n workflow creation system** using three complementary MCP servers:

| MCP Server | Purpose | Status | Configuration File |
|------------|---------|--------|-------------------|
| **n8n-mcp** | Node schemas & workflow management | ✅ Configured | `~/.cursor/mcp.json` |
| **Context7** | Up-to-date documentation | ✅ Configured | `~/.cursor/mcp.json` |
| **Firecrawl** | Web scraping (bonus) | ✅ Configured | `~/.cursor/mcp.json` |

---

## 🔄 Detailed Workflow Creation Flow

### Phase 0: Template Search
```
Your Prompt → Claude Code → n8n-mcp → Your n8n Instance
                    │
                    └─→ Queries existing workflows
                         Returns: Template matches
```

**Tools Used:** `list_nodes`, workflow search capabilities  
**Output:** List of similar workflow templates

---

### Phase 1: Node Discovery
```
Your Prompt → Claude Code → n8n-mcp → Node Schema Database
                    │
                    └─→ search_nodes("HTTP Request")
                         Returns: n8n-nodes-base.httpRequest
                                 typeVersion: 4.2
                                 Available: Yes
```

**Tools Used:** `search_nodes`, `list_nodes`  
**Output:** Exact node type identifiers with versions

---

### Phase 2: Essential Properties
```
Your Prompt → Claude Code → n8n-mcp → Node Properties API
                    │
                    └─→ get_node_essentials(httpRequest)
                         Returns: {
                           required: ["url", "method"],
                           optional: ["authentication", "headers"],
                           types: {...},
                           defaults: {...}
                         }
```

**Tools Used:** `get_node_essentials`  
**Output:** Required and essential optional properties with types

---

### Phase 3: Documentation Review (WITH Context7 + Official Docs)
```
┌─────────────────────────────────────────────────────────────┐
│ Your Prompt → Claude Code                                   │
│                    │                                         │
│         ┌──────────┴──────────┬──────────┐                 │
│         ▼                     ▼            ▼                │
│    n8n-mcp             Context7 MCP    Firecrawl MCP         │
│         │                     │            │                │
│         ▼                     ▼            ▼                │
│  Node Documentation   Current n8n Docs  Official Docs       │
│  (from your instance) (from source)     (docs.n8n.io)       │
│         │                     │            │                │
│         └──────────┬──────────┴───────────┘                │
│                    ▼                                         │
│            COMBINED RESULT:                                 │
│            - Official examples & best practices (docs.n8n.io)│
│              ← TRUMPS ALL (HIGHEST PRIORITY)                │
│            - Node structure (n8n-mcp)                       │
│            - Current API docs (Context7)                    │
│            - Latest auth patterns (Context7)                │
│            - No deprecated code (Context7 catches)          │
└─────────────────────────────────────────────────────────────┘
```

**Tools Used (Priority Order):** 
1. Firecrawl scrape docs.n8n.io - Official documentation ← **HIGHEST PRIORITY - TRUMPS ALL**
2. `tools_documentation` (n8n-mcp) - Node schemas
3. Context7 documentation fetch - Source repo docs ← **Secondary reference**

**Output:** 
- Official docs examples and best practices (from docs.n8n.io) ← **TRUMPS ALL**
- Node usage examples (from n8n-mcp)
- Current n8n documentation (from Context7)
- Latest external API specifications

---

### Phase 4: Workflow Construction (WITH Context7)
```
Your Prompt: "POST to Perplexity API with current auth"
      │
      ▼
┌─────────────────────────────────────────────────────┐
│ Claude Code queries Context7:                       │
│ "What is the current Perplexity API authentication  │
│  method and endpoint format for 2025?"              │
└─────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────┐
│ Context7 returns:                                   │
│ - Endpoint: https://api.perplexity.ai/chat/completions
│ - Auth: Bearer token in Authorization header       │
│ - Request format: {"model": "...", "messages": [...]}
│ - NOT deprecated: API key in custom header         │
└─────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────┐
│ Claude Code combines:                               │
│ - n8n HTTP Request node structure (from Phase 2)   │
│ - Current Perplexity API spec (from Context7)      │
│                                                     │
│ Generates working node configuration                │
└─────────────────────────────────────────────────────┘
```

**Why This Works:**
- n8n-mcp provides the STRUCTURE (how to format the node)
- Context7 provides the CONTENT (what API endpoint/auth to use)
- Together = Working code on first try

---

### Phase 5: Pre-Deployment Validation
```
Complete Workflow JSON
      │
      ▼
┌─────────────────────────────────────────────────────┐
│ Claude Code validates:                              │
│ ✅ All node types exist (n8n-mcp)                   │
│ ✅ All properties are valid (n8n-mcp)               │
│ ✅ All connections are correct (n8n-mcp)            │
│ ✅ No deprecated parameters (Context7)              │
│ ✅ Credentials configured (n8n-mcp)                 │
│ ✅ External APIs use current specs (Context7)       │
└─────────────────────────────────────────────────────┘
      │
      ▼
Production-Ready Workflow JSON
```

---

## 🔑 Key Architectural Principles

### 1. Separation of Concerns

```
┌─────────────────────────────────────────────────────┐
│ n8n-mcp: "STRUCTURE"                                │
│ - What nodes exist                                  │
│ - What parameters are required                      │
│ - How to format the workflow JSON                  │
│ - Validation of n8n-specific structure             │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Context7: "CONTENT"                                  │
│ - What are the CURRENT API endpoints                │
│ - What are the LATEST authentication methods       │
│ - What is the CURRENT request format               │
│ - What parameters are DEPRECATED                    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Claude Code: "ORCHESTRATION"                        │
│ - Queries both servers                              │
│ - Combines structure + content                      │
│ - Validates completeness                            │
│ - Generates production-ready workflow                │
└─────────────────────────────────────────────────────┘
```

---

### 2. Information Layering

```
Layer 1: Your Requirements
"Create BCP pipeline with Perplexity enrichment"
         ↓
Layer 2: n8n-mcp Structure
"Use these nodes: webhook, httpRequest, postgres, slack"
"With these parameters: url, method, authentication..."
         ↓
Layer 3: Context7 Current Data
"Perplexity API endpoint: https://api.perplexity.ai/chat/completions"
"Authentication: Bearer token (NOT deprecated API key header)"
"Request format: {model, messages} (current 2025 spec)"
         ↓
Layer 4: Combined Result
Working workflow with correct structure AND current APIs
```

---

## 🎓 Understanding the Three-Server Ecosystem

### Server Comparison Table

| Aspect | n8n-mcp | Context7 | Firecrawl |
|--------|---------|----------|-----------|
| **Purpose** | n8n workflow management | Up-to-date documentation | Web scraping |
| **Your Use Case** | Every n8n workflow | External API validation | Optional |
| **Data Source** | Your n8n instance | Source repositories | Web pages |
| **Update Frequency** | Real-time | Real-time | On-demand |
| **Authentication** | N8N_API_KEY | CONTEXT7_API_KEY (optional) | FIRECRAWL_API_KEY |
| **Activation** | Automatic (n8n keywords) | Manual (`use context7`) | Manual |
| **Rate Limits** | n8n API limits | Higher with API key | Per plan |

---

### When Each Server Activates

```
Your Prompt: "Create n8n workflow for data pipeline"
             └─→ Activates: n8n-mcp ✓
                             Context7 ✗ (need explicit trigger)
                             Firecrawl ✗

Your Prompt: "Create n8n workflow for data pipeline. use context7"
             └─→ Activates: n8n-mcp ✓
                             Context7 ✓
                             Firecrawl ✗

Your Prompt: "Scrape website and create n8n workflow. use context7"
             └─→ Activates: n8n-mcp ✓
                             Context7 ✓
                             Firecrawl ✓
```

---

## 🚀 Data Flow: Complete Example

### Example: Building BCP Pipeline

**Minute 0: You write prompt**
```
You: "Create BCP intelligence pipeline with Perplexity. use context7"
```

**Minute 1: Phase 0 - Template Search**
```
Claude → n8n-mcp: "Search existing workflows matching 'BCP', 'Perplexity', 'intelligence'"
n8n-mcp → Claude: [List of 3 similar templates from your instance]
Claude: "Found existing BCP templates, will use as reference"
```

**Minute 2: Phase 1 - Node Discovery**
```
Claude → n8n-mcp: search_nodes("webhook")
n8n-mcp → Claude: {name: "Webhook", type: "n8n-nodes-base.webhook", version: 2.1}

Claude → n8n-mcp: search_nodes("HTTP Request")
n8n-mcp → Claude: {name: "HTTP Request", type: "n8n-nodes-base.httpRequest", version: 4.2}

[Same for PostgreSQL, Slack nodes]
```

**Minute 3: Phase 2 - Properties**
```
Claude → n8n-mcp: get_node_essentials("webhook")
n8n-mcp → Claude: {required: ["path", "httpMethod"], optional: ["responseMode"]}

Claude → n8n-mcp: get_node_essentials("httpRequest")
n8n-mcp → Claude: {required: ["url", "method"], optional: ["authentication", "body", "headers"]}

[Same for other nodes]
```

**Minute 4: Phase 3 - Documentation (WITH Context7 + Official Docs)**
```
Claude → n8n-mcp: tools_documentation("httpRequest")
n8n-mcp → Claude: [n8n HTTP Request node documentation]

Claude → Context7: "Current Perplexity API documentation 2025"
Context7 → Claude: {
  endpoint: "https://api.perplexity.ai/chat/completions",
  auth: "Bearer token in Authorization header",
  request: {model: "sonar", messages: [...]},
  deprecated: ["API-Key header method (use Bearer instead)"]
}

Claude → Firecrawl: Scrape docs.n8n.io/integrations/builtin/nodes/n8n-nodes-base.httpRequest/ ← CHECK FIRST (HIGHEST PRIORITY)
Firecrawl → Claude: [Official n8n HTTP Request documentation with examples, best practices, common use cases] ← TRUMPS ALL
```

**Minute 5-7: Phase 4 - Construction**
```
Claude combines:
- Node structure from n8n-mcp
- Current API specs from Context7
- Generates complete workflow JSON
```

**Minute 8: Phase 5 - Validation**
```
Claude → n8n-mcp: validate_workflow({...complete JSON...})
n8n-mcp → Claude: ✅ All validations passed

Claude verifies with Context7:
- Perplexity API call uses current endpoint ✅
- Authentication uses Bearer token (not deprecated API-Key) ✅
- Request format matches 2025 spec ✅
```

**Minute 9: Delivery**
```
Claude → You: "Here's your production-ready BCP intelligence pipeline:
              - All nodes validated
              - Current Perplexity API spec (2025)
              - No deprecated parameters
              - Ready to import"
```

---

## 📊 Architecture Benefits

### Without Context7 (Old Way)
```
Your Prompt → Claude Code → n8n-mcp → Your n8n Instance
                    │
                    └─→ Uses AI training data from 2023
                         ⚠️ Might use old Perplexity API format
                         ⚠️ Might use deprecated auth method
                         ⚠️ Might have outdated parameters

Result: ❌ 401 authentication errors, broken API calls
```

---

### With Context7 (New Way)
```
Your Prompt → Claude Code → n8n-mcp → Your n8n Instance
                    │          (structure)
                    │
                    └─→ Context7 → Source Repositories
                                    (current content)

                    Combines: Structure + Current APIs

Result: ✅ Working workflow with 2025 API specs
```

---

## 🎯 Your Current Architecture

```
┌────────────────────────────────────────────────────────┐
│                    ~/.cursor/mcp.json                  │
├────────────────────────────────────────────────────────┤
│                                                        │
│  "n8n": {                                              │
│    "command": "npx -y n8n-mcp"                         │
│    "env": {                                            │
│      "N8N_API_KEY": "..."        ← Your n8n instance   │
│      "N8N_URL": "ibeylin.app..."                       │
│    }                                                   │
│  }                                                     │
│                                                        │
│  "Context7": {                                         │
│    "url": "mcp.context7.com/mcp" ← Up-to-date docs     │
│  }                                                     │
│                                                        │
│  "firecrawl": {                                        │
│    "command": "npx -y firecrawl-mcp"                   │
│  }                                                     │
└────────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│                     Cursor IDE                         │
│                                                        │
│  Claude Code has access to:                           │
│  ✅ Your n8n instance (via n8n-mcp)                    │
│  ✅ Current documentation (via Context7)               │
│  ✅ Web scraping (via Firecrawl)                       │
│                                                        │
│  Result: Production-ready workflows on first try       │
└────────────────────────────────────────────────────────┘
```

---

## 📋 Common Prompts You Can Use Right Now

### Prompt 1: Simple Data Pipeline
```
Create an n8n workflow that:
- Triggers on webhook POST to /intake
- Validates JSON has required fields (name, email, company)
- Stores data in PostgreSQL
- Sends Slack notification on success

Follow 02_WORKFLOW_CREATION.md 5-phase process

use context7
```

---

### Prompt 2: BCP Intelligence (Your Use Case)
```
Build a BCP intelligence pipeline:

Phase 1: Data Intake
- Webhook receives supplier data (name, location, industry)
- Validate required fields

Phase 2: Enrichment
- Query Perplexity API for market intelligence
- Extract key business insights

Phase 3: Storage
- Store enriched BCP in PostgreSQL
- Create Neo4j knowledge graph relationships

Phase 4: Notification
- Send Slack message with BCP summary
- Include error handling

Use current 2025 API specifications for all external services.

Follow 02_WORKFLOW_CREATION.md 5-phase process

use context7
```

---

### Prompt 3: Update Existing Workflow
```
I have an existing n8n workflow from 2023 with these nodes:
- Webhook Trigger (typeVersion 1)
- HTTP Request to Slack (typeVersion 2)
- Google Sheets append (typeVersion 1)

Update this workflow to use:
- Latest node type versions
- Current authentication patterns (2025)
- Modern error handling
- No deprecated parameters

Follow 02_WORKFLOW_CREATION.md validation process

use context7
```

---

## 🏆 Success Metrics

Your n8n MCP setup is **production-ready** when you can:

- ✅ Create a working workflow in under 10 minutes
- ✅ Zero red dot errors on first import
- ✅ All nodes have correct typeVersions
- ✅ External API calls work immediately (no 401/404 errors)
- ✅ Connections are valid
- ✅ Error handling is implemented

**You have all the tools to achieve this now.**

---

## ✅ Summary

**Your architecture provides:**

1. **Structure Validation** (n8n-mcp)
   - What nodes exist
   - What parameters are required
   - How to format workflow JSON

2. **Content Validation** (Context7)
   - Current API endpoints
   - Latest authentication methods
   - No deprecated code

3. **Orchestration** (Claude Code)
   - Combines both
   - Generates working workflows
   - Validates everything

**Result:** Perfect n8n workflows with zero errors, current APIs, and no deprecated code.

---

**Version:** 2.0 | **Last Updated:** 2025-01-27 | **Status:** ✅ Production Ready

