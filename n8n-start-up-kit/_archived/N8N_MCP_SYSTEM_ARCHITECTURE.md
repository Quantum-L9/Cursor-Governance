# n8n MCP System Architecture Diagram

**Visual guide to your complete n8n workflow creation system**

**Date:** 2025-11-09
**Status:** Production Ready

---

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         YOUR CURSOR IDE                                 │
│                                                                         │
│  You write:                                                             │
│  "Create n8n workflow for BCP intelligence pipeline. use context7"     │
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

## 🔄 Detailed Workflow Creation Flow

### Phase 0: Template Search

```
Your Prompt → Claude Code → n8n-mcp → Your n8n Instance
                    │
                    └─→ Queries existing workflows
                         Returns: Template matches
```

**Tools Used:**
- `list_nodes` - Browse templates by category
- Workflow search capabilities

**Output:** List of similar workflow templates you've created before

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

**Tools Used:**
- `search_nodes` - Find nodes by functionality
- `list_nodes` - Browse by category

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

**Tools Used:**
- `get_node_essentials` - Get 10-20 key properties (not 200+)

**Output:** Required and essential optional properties with types

---

### Phase 3: Documentation Review (WITH Context7)

```
┌─────────────────────────────────────────────────────────────┐
│ Your Prompt → Claude Code                                   │
│                    │                                         │
│         ┌──────────┴──────────┐                             │
│         ▼                     ▼                             │
│    n8n-mcp             Context7 MCP                         │
│         │                     │                             │
│         ▼                     ▼                             │
│  Node Documentation   Current n8n Docs                      │
│  (from your instance) (from source repos)                   │
│         │                     │                             │
│         └──────────┬──────────┘                             │
│                    ▼                                         │
│            COMBINED RESULT:                                 │
│            - Node structure (n8n-mcp)                       │
│            - Current API docs (Context7)                    │
│            - Latest auth patterns (Context7)                │
│            - No deprecated code (Context7 catches)          │
└─────────────────────────────────────────────────────────────┘
```

**Tools Used:**
- `tools_documentation` (n8n-mcp)
- Context7 documentation fetch (triggered by `use context7`)

**Output:**
- Node usage examples
- **Current** n8n documentation (2025)
- **Latest** external API specifications
- Authentication details

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
│ Generates working node configuration:              │
│ {                                                   │
│   "type": "n8n-nodes-base.httpRequest",            │
│   "typeVersion": 4.2,                              │
│   "parameters": {                                  │
│     "url": "https://api.perplexity.ai/chat/completions",
│     "method": "POST",                              │
│     "authentication": "genericCredentialType",     │
│     "headers": {                                   │
│       "Authorization": "Bearer {{$credentials...}}"│
│     },                                             │
│     "body": {                                      │
│       "model": "sonar",                            │
│       "messages": [...]                            │
│     }                                              │
│   }                                                │
│ }                                                  │
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

## 🎯 Information Flow: Real Example

### Example: BCP Intelligence Pipeline with Perplexity

**Your Prompt:**
```
Create BCP intelligence pipeline:
1. Webhook receives supplier data
2. Perplexity API enriches data
3. PostgreSQL stores BCP
4. Slack sends notification

use context7
```

---

### Step-by-Step Flow

**Step 1: Template Search**
```
You → Claude → n8n-mcp
              list_nodes("webhook", "API", "database")
              └─→ Returns: Similar BCP workflows, API integration templates
```

**Step 2: Node Discovery**
```
You → Claude → n8n-mcp
              search_nodes("webhook")
              └─→ n8n-nodes-base.webhook (v2.1)

              search_nodes("HTTP Request")
              └─→ n8n-nodes-base.httpRequest (v4.2)

              search_nodes("PostgreSQL")
              └─→ n8n-nodes-base.postgres (v2.5)

              search_nodes("Slack")
              └─→ n8n-nodes-base.slack (v2.3)
```

**Step 3: Essential Properties**
```
You → Claude → n8n-mcp
              get_node_essentials("webhook")
              └─→ {path, httpMethod, responseMode, ...}

              get_node_essentials("httpRequest")
              └─→ {url, method, authentication, body, ...}

              [Same for PostgreSQL and Slack nodes]
```

**Step 4: Documentation Review**
```
┌──────────────────────────────────────────────────────────┐
│ You → Claude → n8n-mcp + Context7                        │
│                                                          │
│ From n8n-mcp:                                            │
│ - Webhook node configuration structure                  │
│ - HTTP Request node parameters                          │
│ - PostgreSQL connection format                          │
│ - Slack notification structure                          │
│                                                          │
│ From Context7 (triggered by "use context7"):            │
│ - Current Perplexity API endpoint (2025)                │
│ - Latest authentication method (Bearer token)           │
│ - Current request body format                           │
│ - Latest PostgreSQL connection syntax                   │
│ - Current Slack webhook patterns                        │
└──────────────────────────────────────────────────────────┘
```

**Step 5: Workflow Construction**
```
You → Claude → Combines all information

              Builds complete workflow JSON:

              {
                "name": "BCP Intelligence Pipeline",
                "nodes": [
                  {
                    "type": "n8n-nodes-base.webhook",
                    "typeVersion": 2.1,
                    "parameters": {
                      "path": "bcp-intake",
                      "httpMethod": "POST",
                      "responseMode": "onReceived"
                    }
                  },
                  {
                    "type": "n8n-nodes-base.httpRequest",
                    "typeVersion": 4.2,
                    "parameters": {
                      "url": "https://api.perplexity.ai/chat/completions",
                      "method": "POST",
                      "authentication": "genericCredentialType",
                      "headers": {
                        "Authorization": "Bearer {{$credentials.perplexityApi.token}}"
                      },
                      "body": {
                        "model": "sonar",
                        "messages": [
                          {
                            "role": "user",
                            "content": "{{$json.supplierName}} market intelligence"
                          }
                        ]
                      }
                    }
                  },
                  {PostgreSQL node with current syntax},
                  {Slack node with latest webhook format}
                ],
                "connections": {...}
              }
```

**Step 6: Validation**
```
You → Claude → n8n-mcp validate_workflow

              ✅ All nodes exist
              ✅ All properties valid
              ✅ Connections correct
              ✅ TypeVersions current

              Context7 confirms:
              ✅ Perplexity API call uses 2025 spec
              ✅ No deprecated authentication
              ✅ Current request format
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
│ Context7: "CONTENT"                                 │
│ - What are the CURRENT API endpoints               │
│ - What are the LATEST authentication methods       │
│ - What is the CURRENT request format               │
│ - What parameters are DEPRECATED                   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Claude Code: "ORCHESTRATION"                        │
│ - Queries both servers                             │
│ - Combines structure + content                     │
│ - Validates completeness                           │
│ - Generates production-ready workflow              │
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

### 3. Validation at Every Layer

```
┌─────────────────────────────────────────────────────┐
│ Phase 0: Template Search                            │
│ Validation: Do similar workflows exist?             │
│ Benefit: Learn from proven patterns                 │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│ Phase 1: Node Discovery                             │
│ Validation: Does the node exist in your instance?   │
│ Benefit: No broken node references                  │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│ Phase 2: Essential Properties                       │
│ Validation: Are all required properties provided?   │
│ Benefit: No missing configuration                   │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│ Phase 3: Documentation Review                       │
│ Validation: Are we using current docs?              │
│ Benefit: No outdated code patterns                  │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│ Phase 4: Workflow Construction                      │
│ Validation: Are external APIs using current specs?  │
│ Benefit: No 401/404 authentication errors           │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│ Phase 5: Pre-Deployment Validation                  │
│ Validation: Complete workflow check                 │
│ Benefit: Working on first deployment                │
└─────────────────────────────────────────────────────┘
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

**Minute 4: Phase 3 - Documentation (WITH Context7)**
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

**Version:** 1.0
**Last Updated:** 2025-11-09
**Author:** Claude Code (Sonnet 4.5)
