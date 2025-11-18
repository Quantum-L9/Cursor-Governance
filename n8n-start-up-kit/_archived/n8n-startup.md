---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "CMD-N8N-001"
component_name: "n8n Startup Kit Command"
layer: "intelligence"
domain: "n8n_automation"
type: "command"
status: "active"
created: "2025-11-10T00:00:00Z"
updated: "2025-11-10T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["INT-RSN-001"]
integrates_with: ["CMD-001", "CMD-002", "INT-RSN-001"]
api_endpoints: []
data_sources: [".cursor-commands/n8n-start-up-kit/"]
outputs: ["n8n_workflows", "validated_configurations", "deployment_ready_json"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: false
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Load n8n MCP documentation suite in optimal order for workflow creation"
summary: "Slash command that loads complete n8n startup kit with MCP validation, Context7 integration, and 5-phase workflow creation process"
business_value: "Enables rapid n8n workflow development with zero-error validation and current API specifications"
success_metrics: ["workflow_creation_time < 10min", "error_rate = 0", "first_deploy_success >= 0.95"]

# === INTEGRATION METADATA ===
suite_2_origin: "n/a - new command"
migration_notes: "Created to provide instant access to complete n8n MCP documentation suite"

# === TAGS & CLASSIFICATION ===
tags: ["n8n", "workflow", "automation", "mcp", "context7", "command"]
keywords: ["n8n", "workflow", "mcp", "automation", "validation", "context7"]
related_components: ["INT-RSN-001", "CMD-001", "CMD-002"]
startup_required: false
mode_type: "command"
---

name: n8n
description: Load n8n MCP documentation suite in optimal order for workflow creation

# `/n8n` - n8n Startup Kit Command

**Activate Complete n8n MCP Workflow Creation System**

---

## 🎯 What This Command Does

When you type `/n8n`, this command loads the complete n8n MCP documentation suite in the optimal order for AI-assisted workflow creation. It provides:

- ✅ **n8n-mcp validation** - Zero-error node schemas
- ✅ **Context7 integration** - Current 2025 API specifications
- ✅ **5-phase workflow process** - Systematic creation methodology
- ✅ **Copy-paste prompts** - Ready-to-use templates
- ✅ **Real-world examples** - BCP intelligence, data pipelines, API integrations

---

## 📚 Documentation Loading Sequence

**Optimized for AI Assistant Users (8 minutes total reading time)**

### Phase 1: Core Workflow Creation (MANDATORY)
**Purpose:** Master the 5-phase validated workflow creation process

```
READ: @.cursor-commands/n8n-start-up-kit/N8N_WORKFLOW_CREATION_PROMPT.md
├─ Duration: 15 minutes
├─ Lines: 700
├─ Purpose: Complete 5-phase workflow creation system
├─ Contains: Copy-paste prompt templates
└─ Use For: Every workflow you create
```

**Key Sections:**
- Phase 0: Template Search
- Phase 1: Node Discovery (n8n-mcp)
- Phase 2: Essential Properties
- Phase 3: Documentation Review (Context7)
- Phase 4: Workflow Construction (validated JSON)
- Phase 5: Pre-Deployment Validation

### Phase 2: Context7 Integration (MANDATORY)
**Purpose:** Understand how to get current 2025 API specifications

```
READ: @.cursor-commands/n8n-start-up-kit/CONTEXT7_N8N_INTEGRATION_GUIDE.md
├─ Duration: 15 minutes
├─ Lines: 774
├─ Purpose: Context7 + n8n integration for current docs
├─ Contains: API validation, deprecation detection
└─ Use For: External API integrations, updating legacy workflows
```

**Key Sections:**
- Why Context7 eliminates API hallucinations
- How to validate current API specifications
- Real-world use cases (Perplexity, Slack, etc.)
- Integration with 5-phase process

### Phase 3: Quick Reference (MANDATORY)
**Purpose:** Keep handy while building workflows

```
READ: @.cursor-commands/n8n-start-up-kit/N8N_MCP_CHEAT_SHEET.md
├─ Duration: 3 minutes
├─ Lines: 368
├─ Purpose: One-page quick reference
├─ Contains: Common commands, troubleshooting, prompts
└─ Use For: Quick lookups during workflow creation
```

### Phase 4: Quick Start Example (OPTIONAL - First Time Only)
**Purpose:** See a working example

```
READ: @.cursor-commands/n8n-start-up-kit/N8N_QUICK_START.md
├─ Duration: 5 minutes
├─ Lines: 184
├─ Purpose: 5-minute working example
├─ Contains: Hello World workflow
└─ Use For: First-time setup validation
```

### Phase 5: Technical Reference (AS NEEDED)
**Purpose:** Deep technical details when needed

```
READ: @.cursor-commands/n8n-start-up-kit/N8N_NODE_VALIDATION_PROTOCOL.md
├─ Duration: 20 minutes
├─ Lines: 893
├─ Purpose: Complete technical reference
├─ Contains: MCP server details, troubleshooting
└─ Use For: Complex debugging, technical questions
```

### Phase 6: System Architecture (AS NEEDED)
**Purpose:** Understand the complete system

```
READ: @.cursor-commands/n8n-start-up-kit/N8N_MCP_SYSTEM_ARCHITECTURE.md
├─ Duration: 15 minutes
├─ Lines: 668
├─ Purpose: Visual architecture and system design
├─ Contains: Diagrams, flow charts, integration patterns
└─ Use For: Understanding how everything fits together
```

---

## 🚀 Usage

### Basic Usage
```
/n8n
```

**What happens:**
1. Loads all documentation files in optimal order
2. Activates n8n reasoning profile (INT-RSN-001)
3. Enables MCP tool selection protocol
4. Ready to create validated workflows

### After Loading - Create Your First Workflow

**Copy-Paste Prompt Template:**
```
Create an n8n workflow that:
- [Describe your automation]

Follow N8N_WORKFLOW_CREATION_PROMPT.md 5-phase process.
use context7
```

**Example - Simple Data Pipeline:**
```
Create an n8n workflow that:
- Triggers on webhook POST to /intake
- Validates JSON has required fields (name, email, company)
- Stores data in PostgreSQL table "leads"
- Sends Slack notification to #sales channel

Follow N8N_WORKFLOW_CREATION_PROMPT.md 5-phase process.
use context7
```

**Example - BCP Intelligence Pipeline:**
```
Build a BCP intelligence pipeline:

Phase 1: Data Intake
- Webhook receives supplier data

Phase 2: Enrichment
- Query Perplexity API for market intelligence

Phase 3: Storage
- Store enriched BCP in PostgreSQL
- Create Neo4j knowledge graph relationships

Phase 4: Notification
- Send Slack message with BCP summary

Use current 2025 API specifications.
Follow N8N_WORKFLOW_CREATION_PROMPT.md 5-phase process.
use context7
```

---

## 📋 What You Get After `/n8n`

### Immediate Capabilities
- ✅ **Zero-error workflows** - Validated against your n8n instance
- ✅ **Current APIs** - 2025 specifications via Context7
- ✅ **Correct typeVersions** - No red dot errors
- ✅ **Valid connections** - Proper node linking
- ✅ **Error handling** - Built-in fallbacks
- ✅ **Production-ready** - Deploy immediately

### Available MCP Tools
- **n8n-mcp** - Node schemas, workflow CRUD, validation
- **Context7** - Up-to-date n8n & API documentation
- **Firecrawl** - Web scraping (optional)

### Copy-Paste Prompts
- Simple automation templates
- API integration templates
- Data pipeline templates
- BCP intelligence templates
- Legacy workflow updates

---

## 🎯 Common Use Cases

### Use Case 1: First-Time Workflow Creation
```
/n8n

[After loading]
Create an n8n workflow that sends a Slack message when a webhook is triggered.
Follow N8N_WORKFLOW_CREATION_PROMPT.md 5-phase process.
use context7
```

### Use Case 2: External API Integration
```
/n8n

[After loading]
Create n8n workflow integrating with Perplexity API:
- Query for company intelligence
- Parse response
- Store in PostgreSQL
Use current 2025 Perplexity API specifications.
Follow N8N_WORKFLOW_CREATION_PROMPT.md 5-phase process.
use context7
```

### Use Case 3: Update Legacy Workflow
```
/n8n

[After loading]
I have an existing n8n workflow from 2023 with outdated Slack node.
Update to use:
- Latest Slack node typeVersion
- Current authentication (2025)
- Modern error handling
Follow N8N_WORKFLOW_CREATION_PROMPT.md validation.
use context7
```

---

## 🔧 Configuration

### Your Current Setup
**Location:** `~/.cursor/mcp.json`

**Configured Servers:**
- ✅ n8n-mcp (API key to https://ibeylin.app.n8n.cloud)
- ✅ Context7 (remote server)
- ✅ Firecrawl (API key configured)

**Status:** Production ready

---

## 📊 Success Metrics

You'll know `/n8n` is working when:
- ✅ Create workflows in under 10 minutes
- ✅ Zero red dot errors on first import
- ✅ All nodes have correct typeVersions
- ✅ External API calls work immediately
- ✅ No deprecated parameters

---

## 🔗 Integration with Suite 6

### Reasoning Profile Integration
When `/n8n` is activated, it automatically integrates with:
- **reasoning_n8n.md** (INT-RSN-001) - n8n-specific reasoning
- **MCP Tool Selection Protocol** - Choose best MCP tool for each task
- **YNP Mode** (CMD-001) - Strategic co-pilot for workflow creation

### Workflow
1. Type `/n8n` to load documentation
2. Use copy-paste prompt template
3. AI follows 5-phase validation process
4. Get production-ready workflow JSON
5. Import to n8n instance
6. Test and deploy

---

## 📖 Documentation Index

**Full documentation available at:**
```
@.cursor-commands/n8n-start-up-kit/INDEX.md
```

**Complete file list:**
1. README.md - Complete overview
2. N8N_QUICK_START.md - 5-minute example
3. N8N_WORKFLOW_CREATION_PROMPT.md - 5-phase process
4. CONTEXT7_N8N_INTEGRATION_GUIDE.md - Current API specs
5. N8N_NODE_VALIDATION_PROTOCOL.md - Technical reference
6. N8N_MCP_COMPLETE_SETUP_SUMMARY.md - System overview
7. N8N_MCP_SYSTEM_ARCHITECTURE.md - Architecture diagrams
8. N8N_MCP_CHEAT_SHEET.md - Quick reference
9. INDEX.md - Navigation guide

**Total:** 168KB, 4,000+ lines, 100% complete

---

## 🎓 Learning Outcomes

After using `/n8n`, you will be able to:
1. ✅ Create perfect n8n workflows with zero errors
2. ✅ Integrate external APIs with current 2025 specifications
3. ✅ Use Context7 to eliminate API hallucinations
4. ✅ Validate workflows before deployment
5. ✅ Troubleshoot common errors
6. ✅ Update legacy workflows to modern standards
7. ✅ Build complex multi-step automations
8. ✅ Deploy workflows to production
9. ✅ Use all three MCP servers effectively
10. ✅ Create custom workflows for your BCP project

---

## 🚨 Important Notes

### Always Include in Prompts
When creating workflows after `/n8n`, always add:
```
Follow N8N_WORKFLOW_CREATION_PROMPT.md 5-phase process.
use context7
```

This ensures:
- ✅ Proper validation against your n8n instance
- ✅ Current API specifications (not outdated training data)
- ✅ Correct node typeVersions
- ✅ Valid connections
- ✅ Error handling

### MCP Tool Selection
The system will automatically:
- Use **n8n-mcp** for node schemas and validation
- Use **Context7** for current API documentation
- Use **Firecrawl** for web scraping (if needed)

You don't need to specify which tool - the AI will select appropriately.

---

## 📞 Support

### Documentation Location
```
/Users/ib-mac/Dropbox/Prompt_Repo_IB/Load_Pack/Cursor_load pack/.cursor-commands/n8n-start-up-kit/
```

### Your n8n Instance
- **URL:** https://ibeylin.app.n8n.cloud
- **API Key:** Configured in `~/.cursor/mcp.json`

### External Resources
- **n8n Docs:** https://docs.n8n.io
- **n8n Community:** https://community.n8n.io
- **Context7 Dashboard:** https://context7.com/dashboard

---

## ✅ Verification

After running `/n8n`, verify:
```
✅ n8n documentation loaded
   - N8N_WORKFLOW_CREATION_PROMPT.md (5-phase process)
   - CONTEXT7_N8N_INTEGRATION_GUIDE.md (current APIs)
   - N8N_MCP_CHEAT_SHEET.md (quick reference)
   - n8n reasoning profile active (INT-RSN-001)
   - MCP tool selection protocol enabled
   - Ready to create validated workflows
```

---

**Ready to build perfect n8n workflows with zero errors!**

**Version:** 1.0
**Status:** ✅ Active
**Last Updated:** 2025-11-10


