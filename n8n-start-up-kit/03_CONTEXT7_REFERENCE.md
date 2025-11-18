---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-N8N-003"
component_name: "Context7 Integration Reference"
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
integrates_with: ["INT-N8N-002", "context7-mcp"]
api_endpoints: []
data_sources: ["context7-mcp"]
outputs: ["current_api_docs", "validation_reports"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: false
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Context7 MCP integration guide for up-to-date n8n and API documentation"
summary: "Complete reference for eliminating API hallucination with current documentation, quick reference commands, and troubleshooting"
business_value: "Ensures zero-error workflow creation with current 2025 API specifications and no deprecated code"
success_metrics: ["api_accuracy >= 0.95", "deprecation_detection_rate >= 0.90"]

# === TAGS & CLASSIFICATION ===
tags: ["n8n", "context7", "api", "documentation", "quick-reference"]
keywords: ["context7", "n8n", "api", "documentation", "current", "deprecated"]
related_components: ["INT-N8N-001", "INT-N8N-002"]
startup_required: false
mode_type: "documentation"
---

# Context7 + n8n Integration Reference

**Purpose:** Eliminate API hallucination with up-to-date documentation + official n8n docs | **Version:** 2.1 | **Last Updated:** 2025-01-27

---

## 🎯 The 3-Second Summary

```
Your Prompt + "use context7" + Official docs → Perfect n8n Workflow
                                                (structure from n8n-mcp)
                                                (content from Context7)
                                                (best practices from docs.n8n.io)
```

---

## 📚 What is Context7 MCP?

Context7 eliminates API hallucination by providing:
- **Up-to-date, version-specific documentation** directly in your AI prompt
- **Real code examples** from source repositories
- **No outdated APIs** or deprecated patterns
- **No tab-switching** required

**Key Benefit:** Context7 fetches current documentation while n8n-mcp provides node schemas - together they ensure both **accurate n8n workflows** and **correct API usage**.

---

## 🔄 How Context7 Complements n8n-mcp + Official Docs

### The Three-Source Strategy

| Source | Purpose | What It Provides |
|--------|---------|------------------|
| **n8n-mcp** | n8n-specific workflow management | Node schemas, workflow CRUD, execution monitoring |
| **Context7** | Up-to-date documentation | Current n8n APIs, latest node documentation, version-specific features |
| **Official docs.n8n.io** | Authoritative reference | Curated examples, best practices, real-world use cases |

**Why Use All Three?**
1. **Official docs** tells you WHAT n8n recommends (best practices and examples) ← **TRUMPS ALL - CHECK FIRST**
2. **n8n-mcp** tells you WHAT nodes exist and HOW to configure them (structure)
3. **Context7** tells you CURRENT documentation for those nodes (content from source repos) ← **Secondary reference**
4. Together = No broken workflows + Official best practices (trumps all) + Current code

---

## ⚙️ Configuration

### Your Current Setup

**Location:** `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "Context7": {
      "url": "https://mcp.context7.com/mcp",
      "headers": {}
    },
    "n8n": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "N8N_API_KEY": "your-api-key",
        "N8N_URL": "https://ibeylin.app.n8n.cloud"
      }
    }
  }
}
```

### Enhanced Setup with API Key (Recommended)

**Get API Key:** https://context7.com/dashboard

**Update Configuration:**
```json
{
  "mcpServers": {
    "Context7": {
      "url": "https://mcp.context7.com/mcp",
      "headers": {
        "CONTEXT7_API_KEY": "your-context7-api-key-here"
      }
    }
  }
}
```

**Benefits:** Higher rate limits, access to private documentation, priority support

---

## 🚀 Usage Pattern

### Standard Prompt (Without Context7)
```
Create an n8n workflow that:
- Triggers on webhook POST to /data-intake
- Validates incoming JSON
- Sends data to external API

Follow 02_WORKFLOW_CREATION.md 5-phase process
```

### Enhanced Prompt (With Context7 + Official Docs)
```
Create an n8n workflow that:
- Triggers on webhook POST to /data-intake
- Validates incoming JSON
- Sends data to external API

Follow 02_WORKFLOW_CREATION.md 5-phase process

In Phase 3, check (in priority order):
1. Official docs.n8n.io (authoritative examples and best practices) ← **CHECK FIRST (HIGHEST PRIORITY - TRUMPS ALL)**
2. n8n-mcp tools_documentation (node schemas)
3. Context7 (current source repo docs) ← **Secondary reference**

use context7
```

**What Changes:**
- Adding `use context7` triggers real-time documentation lookup
- AI receives current n8n API documentation
- Checking official docs.n8n.io provides authoritative examples
- Ensures latest node configurations and parameters
- Eliminates deprecated code patterns
- Includes n8n-recommended best practices

---

## 📋 Copy-Paste Prompt Template

```markdown
## Project: [Your Workflow Name]

### Objective
[What should the workflow do?]

### Requirements
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]

### Instructions
Follow 02_WORKFLOW_CREATION.md 5-phase process:
- Phase 0: Template Search
- Phase 1: Node Discovery
- Phase 2: Essential Properties
- Phase 3: Documentation Review
- Phase 4: Workflow Construction
- Phase 5: Pre-Deployment Validation

use context7
```

---

## ⚡ Common Prompts

### 1. Simple Data Pipeline
```
Create n8n workflow:
- Webhook receives data
- Validate JSON
- Store in PostgreSQL
- Send Slack notification

Follow 02_WORKFLOW_CREATION.md process
use context7
```

### 2. API Integration
```
Create n8n HTTP Request node for [API name]:
- Endpoint: [URL]
- Authentication: [Method]
- Use current 2025 API spec

use context7
```

### 3. Update Legacy Workflow
```
Update this 2023 n8n workflow:
[Paste your workflow description]

Use latest node versions and 2025 best practices
use context7
```

---

## 🎯 When to Use Context7

### ✅ ALWAYS Use Context7 When:
- Working with external APIs (Slack, Google, Perplexity, etc.)
- Using newly released n8n features (< 6 months old)
- Building production workflows
- Updating legacy workflows
- Getting authentication errors

### ⚠️ Optional (Less Value) When:
- Using basic nodes (Manual Trigger, Set, IF, Switch)
- Following exact templates you already have
- Simple 2-3 node workflows

---

## 📊 The 5-Phase Process with Context7 + Official Docs

```
Phase 0: Template Search → Find existing patterns
Phase 1: Node Discovery → Identify exact nodes needed
Phase 2: Essential Properties → Get required configurations
Phase 3: Documentation Review → n8n-mcp + Context7 + Official docs.n8n.io ← ENHANCED
Phase 4: Workflow Construction → Build JSON + Context7 validate APIs
Phase 5: Pre-Deployment Validation → Final checks
```

**Documentation Sources (Phase 3) - Priority Order:**
1. **Official docs.n8n.io:** Authoritative examples and best practices (what n8n recommends) ← **HIGHEST PRIORITY - TRUMPS ALL**
2. **n8n-mcp:** Node schemas from your instance (what exists)
3. **Context7:** Current source repository docs (what's in code) ← **Secondary reference**

**Why Check Official Docs?**
- Complete real-world examples
- Curated best practices
- Version-specific migration guides
- Community workflow patterns

**Context7 Integration Points:**
- **Phase 3:** Fetch current n8n documentation (not outdated training data)
- **Phase 4:** Validate external API calls use 2025 specifications

---

## 🔧 Troubleshooting Fast Fixes

| Problem | Fix |
|---------|-----|
| **Red dot in MCP settings** | Restart Cursor |
| **Context7 not working** | Add `use context7` to prompt |
| **401 API errors** | Use Context7 for current auth |
| **Deprecated parameters** | Add `use context7` to prompt |
| **Wrong typeVersion** | Let n8n-mcp validate |

---

## 🔑 Key Commands

| Task | Command/Prompt |
|------|----------------|
| **Search nodes** | "What n8n nodes are available for [functionality]?" |
| **Get node details** | "Get essential properties for [node name]" |
| **Current API docs** | "Get current [API] documentation. use context7" |
| **Validate workflow** | "Validate this n8n workflow: [paste JSON]" |
| **Update workflow** | "Update this workflow to use current APIs. use context7" |

---

## 📁 Your Configuration

```
Location: ~/.cursor/mcp.json

Configured:
✅ n8n-mcp (https://ibeylin.app.n8n.cloud)
✅ Context7 (remote server)
✅ Firecrawl (web scraping)

Status: Production Ready
```

**Recommended:** Add Context7 API key from https://context7.com/dashboard

---

## ⚙️ MCP Server Quick Reference

| Server | Provides | When It Activates |
|--------|----------|-------------------|
| **n8n-mcp** | Node schemas, workflow CRUD | Automatic (n8n keywords) |
| **Context7** | Current docs, API specs | Manual (`use context7`) |
| **Firecrawl** | Web scraping | Manual (scraping keywords) |

---

## 🎓 Information Hierarchy

```
┌─────────────────────────────────────┐
│ 1. n8n-mcp: STRUCTURE               │
│    - What nodes exist               │
│    - Required parameters            │
│    - Workflow format                │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ 2. Context7: CONTENT                │
│    - Current API endpoints          │
│    - Latest auth methods            │
│    - No deprecated code             │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ 3. Claude Code: ORCHESTRATION       │
│    - Combines structure + content   │
│    - Validates everything           │
│    - Generates working workflow     │
└─────────────────────────────────────┘
```

---

## ✅ Success Checklist

Before deploying, verify:
- ✅ All node types exist in your instance
- ✅ All required properties configured
- ✅ TypeVersions are current
- ✅ Connections are valid
- ✅ Credentials placeholders set
- ✅ External APIs use 2025 specs (Context7)
- ✅ Error handling implemented

---

## 🚀 Deployment Quick Steps

```
1. Save workflow JSON to file
2. Login to https://ibeylin.app.n8n.cloud
3. Click "+ Add workflow"
4. Click ⋮ menu → "Import from File"
5. Select JSON file
6. Configure credentials
7. Click "Test workflow"
8. Verify output
9. Click "Save" → "Activate"
```

---

## 🎯 Common Use Cases at a Glance

### BCP Intelligence Pipeline
```
Webhook → Perplexity API → PostgreSQL → Neo4j → Slack
Guide: 03_CONTEXT7_REFERENCE.md Use Case 3
```

### Data Validation Pipeline
```
Webhook → Validate JSON → PostgreSQL → Slack
Guide: 06_QUICK_START.md
```

### API Integration
```
Trigger → HTTP Request (current API) → Process → Store
Guide: 03_CONTEXT7_REFERENCE.md Example 1
```

### Legacy Update
```
Old Workflow → Analyze → Update versions → Modernize auth
Guide: 03_CONTEXT7_REFERENCE.md Use Case 1
```

---

## 📞 Quick Help

| Issue | Where to Look |
|-------|---------------|
| **Setup issues** | [06_QUICK_START.md](06_QUICK_START.md) |
| **Validation errors** | [04_VALIDATION_PROTOCOL.md](04_VALIDATION_PROTOCOL.md) |
| **API errors** | [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md) |
| **How-to questions** | [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md) |
| **System understanding** | [05_SYSTEM_ARCHITECTURE.md](05_SYSTEM_ARCHITECTURE.md) |

---

## 💡 Pro Tips

1. **Always use `use context7`** for external APIs
2. **Start with template search** (Phase 0) to learn from existing workflows
3. **Copy-paste prompt template** instead of writing from scratch
4. **Validate before deploying** (Phase 5 checklist)
5. **Add Context7 API key** for higher rate limits

---

## 🎉 One-Liner Summary

```
Perfect n8n workflows = Your prompt + n8n-mcp (structure) + Context7 (content) + 5-phase validation
```

---

## 📱 Mobile-Friendly Quick Command

**Just copy-paste this:**
```
Create n8n workflow for [DESCRIBE YOUR AUTOMATION].
Follow 02_WORKFLOW_CREATION.md 5-phase process.
use context7
```

**Replace [DESCRIBE YOUR AUTOMATION] with your use case.**

---

**Version:** 2.1 | **Last Updated:** 2025-01-27 | **Status:** ✅ Production Ready

---

## 📚 Official n8n Documentation Integration

### Why Check Official Docs?

The official n8n documentation website (docs.n8n.io) provides:

- **Authoritative examples:** Curated by n8n team, tested and verified
- **Best practices:** Recommended patterns and anti-patterns
- **Real-world use cases:** Complete workflow examples
- **Version-specific guides:** Migration guides for version updates
- **Community patterns:** Links to proven community workflows

### How to Access Official Docs in Phase 3

**Using Firecrawl MCP (already configured):**

```
"Scrape the official n8n documentation for [node name] from:
https://docs.n8n.io/integrations/builtin/nodes/[node-name]/

Focus on:
- Usage examples
- Configuration best practices
- Common use cases
- Known limitations
- Authentication patterns"
```

**Example URLs:**
- HTTP Request: `https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httpRequest/`
- Webhook: `https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/`
- Slack: `https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.slack/`

### Documentation Source Hierarchy

```
Priority 1: Official docs.n8n.io (Authoritative) ← HIGHEST PRIORITY
  └─→ What n8n officially recommends
  └─→ Curated examples and best practices
  └─→ Real-world use cases
  └─→ TRUMPS all other sources for official guidance

Priority 2: n8n-mcp (Your Instance)
  └─→ What nodes/types exist in YOUR n8n instance
  └─→ Validates against actual available nodes

Priority 3: Context7 (Source Repos) ← Secondary reference
  └─→ What's in the source code
  └─→ Current API specifications
  └─→ Latest changes and deprecations
  └─→ Use when official docs unavailable or need code-level details
```

**Combined Result:** Complete understanding with official guidance (trumps all) + instance validation + current code

