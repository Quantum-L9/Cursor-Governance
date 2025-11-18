---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-N8N-001"
component_name: "n8n MCP Documentation Suite"
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
dependencies: []
integrates_with: ["INT-RSN-001", "CMD-N8N-001"]
api_endpoints: []
data_sources: ["n8n-mcp", "context7-mcp", "firecrawl-mcp"]
outputs: ["n8n_workflows", "validated_configurations"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: false
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Complete n8n workflow creation system with zero-error validation and current API specifications"
summary: "Production-ready documentation suite for creating perfect n8n workflows using MCP validation, Context7 integration, and 5-phase workflow creation process"
business_value: "Enables rapid n8n workflow development with zero errors, correct configurations, and current 2025 API specifications"
success_metrics: ["workflow_creation_time < 10min", "error_rate = 0", "first_deploy_success >= 0.95"]

# === TAGS & CLASSIFICATION ===
tags: ["n8n", "workflow", "automation", "mcp", "context7", "documentation"]
keywords: ["n8n", "workflow", "mcp", "automation", "validation", "context7"]
related_components: ["INT-RSN-001", "CMD-N8N-001"]
startup_required: false
mode_type: "documentation"
---

# n8n MCP Workflow Creation System

**Complete documentation suite for creating perfect n8n workflows with zero errors**

**Status:** ✅ Production Ready | **Version:** 2.0 | **Last Updated:** 2025-01-27

---

## 🚀 Quick Start (5 Minutes)

**New to this system?** Start here:

1. **Read:** [06_QUICK_START.md](06_QUICK_START.md) (5 minutes)
2. **Import:** The Hello World workflow example
3. **Test:** Run it in your n8n instance
4. **Create:** Use [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md) prompt template

**Already familiar?** Jump to [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md) and start building.

---

## 📚 Documentation Suite (6 Files)

### Core Guides (Read in Order)

| File | Purpose | When to Use | Read Time |
|------|---------|-------------|-----------|
| **[01_README.md](01_README.md)** | Complete overview ← **YOU ARE HERE** | First-time setup | 10 min |
| **[06_QUICK_START.md](06_QUICK_START.md)** | 5-minute working example | First workflow | 5 min |
| **[02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md)** | AI prompt template (5-phase process) | Every workflow creation | 15 min |
| **[03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md)** | Context7 + n8n integration | External APIs, current docs | 10 min |
| **[04_VALIDATION_PROTOCOL.md](04_VALIDATION_PROTOCOL.md)** | Complete technical reference | Deep technical questions | 20 min |
| **[05_SYSTEM_ARCHITECTURE.md](05_SYSTEM_ARCHITECTURE.md)** | System overview + architecture | Understanding system | 15 min |
| **n8n_api_helper.py** | Python utility functions | Programmatic workflow management | - |

**Total:** 6 files, ~75 minutes reading time → Production ready

---

## 🎯 What This System Does

### The Problem
Creating n8n workflows manually causes:
- ❌ Red dot errors from wrong typeVersions
- ❌ Deprecated parameters breaking workflows
- ❌ Outdated API authentication patterns
- ❌ Broken connections from typos
- ❌ Hours of debugging

### The Solution
This MCP-powered system provides:
- ✅ AI validates nodes against your actual n8n instance
- ✅ Correct typeVersions automatically
- ✅ Current parameters (Context7 catches deprecations)
- ✅ Latest API specs from 2025
- ✅ Valid connections guaranteed
- ✅ Working workflows in minutes

---

## ⚙️ System Architecture

### Three MCP Servers Working Together

```
┌─────────────────────────────────────────────────────┐
│ n8n-mcp                                             │
│ Provides: Node schemas, workflow CRUD, validation  │
│ Your setup: ✅ Configured                           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Context7 MCP                                        │
│ Provides: Up-to-date n8n & API documentation       │
│ Your setup: ✅ Configured                           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Firecrawl MCP (Optional)                            │
│ Provides: Web scraping capabilities                │
│ Your setup: ✅ Configured                           │
└─────────────────────────────────────────────────────┘
```

**Learn More:** [05_SYSTEM_ARCHITECTURE.md](05_SYSTEM_ARCHITECTURE.md)

---

## 🔄 Workflow Creation Process

### The 5-Phase Sequence

```
Phase 0: Template Search
  ↓ Find existing patterns to build upon
Phase 1: Node Discovery
  ↓ Identify exact nodes needed
Phase 2: Essential Properties
  ↓ Get required configurations
Phase 3: Documentation Review
  ↓ Review docs (n8n-mcp + Context7 + Official docs.n8n.io)
Phase 4: Workflow Construction
  ↓ Build complete JSON with validation
Phase 5: Pre-Deployment Validation
  ↓ Final checks before deployment

Result: Production-ready workflow
```

**Documentation Sources in Phase 3 (Priority Order):**
1. **Official docs.n8n.io:** Authoritative examples and best practices (what n8n recommends) ← **HIGHEST PRIORITY - TRUMPS ALL**
2. **n8n-mcp:** Validates against your instance (what exists)
3. **Context7:** Current source repo docs (what's in code) ← **Secondary reference**

**Detailed Guide:** [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md)

---

## 📖 How to Use This System

### For Complete Beginners

**Path:** Quick Start → Workflow Prompt → Create Your First Workflow

1. Read [06_QUICK_START.md](06_QUICK_START.md) (5 minutes)
2. Import the Hello World example
3. Test it in your n8n instance
4. Copy a prompt template from [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md)
5. Paste into Cursor and create your first validated workflow

**Time to first working workflow:** ~15 minutes

---

### For AI Assistant Users (Claude/Cursor)

**Path:** Workflow Prompt → Context7 Integration → Build

1. Open [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md)
2. Copy the prompt template
3. Fill in your workflow requirements
4. Add `use context7` at the end
5. Paste into Cursor
6. Watch the 5-phase validation process

**Reference when needed:**
- [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md) - When working with external APIs
- [04_VALIDATION_PROTOCOL.md](04_VALIDATION_PROTOCOL.md) - For technical details

---

### For Developers Building Production Workflows

**Path:** All Guides → Deep Technical Reference → Production Deployment

1. **Understand the system:** [05_SYSTEM_ARCHITECTURE.md](05_SYSTEM_ARCHITECTURE.md)
2. **Master Context7:** [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md)
3. **Reference protocol:** [04_VALIDATION_PROTOCOL.md](04_VALIDATION_PROTOCOL.md)
4. **Use prompt template:** [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md)
5. **Deploy:** Follow real-world deployment tutorial

**Time to production-ready complex workflow:** ~30 minutes

---

## 🎓 Common Use Cases

### Use Case 1: Simple Data Pipeline

**Example:** Webhook → Validate → Store → Notify

**Guide:** [06_QUICK_START.md](06_QUICK_START.md) + [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md)

**Prompt Template:**
```
Create an n8n workflow that:
- Triggers on webhook POST to /intake
- Validates JSON has required fields
- Stores data in PostgreSQL
- Sends Slack notification

Follow 02_WORKFLOW_CREATION.md 5-phase process
use context7
```

**Time:** ~10 minutes

---

### Use Case 2: BCP Intelligence Pipeline (Complex)

**Example:** Webhook → Perplexity API → PostgreSQL → Neo4j → Slack

**Guide:** [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md) Use Case 3

**Prompt Template:**
```
Build a BCP intelligence pipeline:
Phase 1: Data Intake - Webhook receives supplier data
Phase 2: Enrichment - Query Perplexity API for market intelligence
Phase 3: Storage - Store enriched BCP in PostgreSQL + Neo4j
Phase 4: Notification - Send Slack message with BCP summary

Use current 2025 API specifications.
Follow 02_WORKFLOW_CREATION.md 5-phase process
use context7
```

**Time:** ~20 minutes

---

### Use Case 3: Update Legacy Workflow

**Example:** Modernize 2023 workflow with current APIs

**Guide:** [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md) Use Case 1

**Prompt Template:**
```
I have an existing n8n workflow from 2023 with:
- [List your nodes and versions]

Update to use:
- Latest node type versions
- Current authentication patterns (2025)
- Modern error handling

Follow 02_WORKFLOW_CREATION.md validation
use context7
```

**Time:** ~15 minutes

---

## 🔧 Configuration

### Your Current Setup

**Location:** `~/.cursor/mcp.json`

**Configured Servers:**
- ✅ n8n-mcp (with API key to https://ibeylin.app.n8n.cloud)
- ✅ Context7 (remote server)
- ✅ Firecrawl (with API key)

**Status:** Production ready

### Recommended Enhancement

**Add Context7 API Key** for higher rate limits:

1. Visit https://context7.com/dashboard
2. Get API key
3. Update `~/.cursor/mcp.json`:
```json
"Context7": {
  "url": "https://mcp.context7.com/mcp",
  "headers": {
    "CONTEXT7_API_KEY": "your-key-here"
  }
}
```
4. Restart Cursor

**Learn More:** [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md#configuration)

---

## 📋 Copy-Paste Prompts

### Prompt 1: Simple Automation
```
Using n8n-mcp, create a workflow that:
- [Describe your automation]

Follow 02_WORKFLOW_CREATION.md 5-phase process
use context7
```

### Prompt 2: API Integration
```
Create n8n workflow integrating with [API name]:
- [List requirements]
- Use current [API name] 2025 specifications

Follow 02_WORKFLOW_CREATION.md 5-phase process
use context7
```

### Prompt 3: Data Pipeline
```
Build n8n data pipeline:
Phase 1: [Data source]
Phase 2: [Processing/enrichment]
Phase 3: [Storage]
Phase 4: [Notification/output]

Follow 02_WORKFLOW_CREATION.md 5-phase process
use context7
```

**More Examples:** See [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md#prompt-templates)

---

## 🎯 Quick Reference

### When to Use What

| Task | Primary Guide | Secondary Reference |
|------|---------------|---------------------|
| First-time setup | [06_QUICK_START.md](06_QUICK_START.md) | - |
| Create any workflow | [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md) | [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md) |
| External API integration | [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md) | [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md) |
| Update legacy workflow | [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md) | [04_VALIDATION_PROTOCOL.md](04_VALIDATION_PROTOCOL.md) |
| Troubleshoot errors | [04_VALIDATION_PROTOCOL.md](04_VALIDATION_PROTOCOL.md) | [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md) |
| Understand system | [05_SYSTEM_ARCHITECTURE.md](05_SYSTEM_ARCHITECTURE.md) | [01_README.md](01_README.md) |

---

## ✅ Success Criteria

You'll know this system is working when:

- ✅ Create workflows in under 10 minutes
- ✅ Zero red dot errors on first import
- ✅ All nodes have correct typeVersions
- ✅ External API calls work immediately
- ✅ Connections are valid
- ✅ Error handling is implemented
- ✅ No deprecated parameters

**You have all the tools to achieve this.**

---

## 📞 Support & Resources

### Documentation (Local)
All guides in this directory - see table above

### External Resources
- **n8n Documentation:** https://docs.n8n.io
- **n8n Community:** https://community.n8n.io
- **n8n-mcp GitHub:** https://github.com/czlonkowski/n8n-mcp
- **Context7 Dashboard:** https://context7.com/dashboard
- **Context7 GitHub:** https://github.com/upstash/context7

### Your n8n Instance
- **URL:** https://ibeylin.app.n8n.cloud
- **API Key:** Configured in `~/.cursor/mcp.json`

---

## 🚀 Next Steps

### Immediate Actions

1. **Test your setup**
   - Restart Cursor to activate MCP servers
   - Check Settings → MCP Servers for green indicators

2. **Create first workflow**
   - Use Prompt 1, 2, or 3 from above
   - Paste into Cursor
   - Watch the 5-phase process

3. **Import and test**
   - Follow deployment tutorial in [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md)
   - Test in your n8n instance

---

### For Your BCP Project

**You can now:**
- Automate BCP creation with Perplexity AI
- Use current 2025 API specifications
- Build complex multi-step workflows
- Update legacy workflows
- Eliminate errors and broken nodes

**Start building:** [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md)

---

## 🎉 Summary

**You now have:**
- ✅ Complete MCP setup (n8n-mcp + Context7 + Firecrawl)
- ✅ 6 comprehensive guides (consolidated from 11 files)
- ✅ Production-ready workflow creation system
- ✅ Up-to-date API validation
- ✅ Copy-paste prompt templates
- ✅ Real-world examples

**What this means:**
Create perfect n8n workflows with zero errors, correct configurations, no deprecated nodes, and current API specifications - all in minutes instead of hours.

---

**Ready to build?** Start with [06_QUICK_START.md](06_QUICK_START.md) or jump to [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md)!

---

**Version:** 2.0 | **Last Updated:** 2025-01-27 | **Status:** ✅ Production Ready

