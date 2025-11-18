# n8n MCP Quick Reference Cheat Sheet

**One-page reference for creating perfect n8n workflows**

**Print this page for easy reference while building workflows**

---

## 🎯 The 3-Second Summary

```
Your Prompt + "use context7" → Perfect n8n Workflow
                                (structure from n8n-mcp)
                                (content from Context7)
```

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
Follow the 5-phase validation process from N8N_WORKFLOW_CREATION_PROMPT.md:

Phase 0: Template Search
Phase 1: Node Discovery
Phase 2: Essential Properties
Phase 3: Documentation Review
Phase 4: Workflow Construction
Phase 5: Pre-Deployment Validation

use context7
```

**Full template:** [N8N_WORKFLOW_CREATION_PROMPT.md](N8N_WORKFLOW_CREATION_PROMPT.md#prompt-template)

---

## 🚀 Quick Start Commands

### First Time Setup

```bash
# 1. Check MCP servers in Cursor
Settings → MCP Servers → Verify green indicators

# 2. Restart Cursor if you just configured MCP
Cmd+Q → Reopen Cursor

# 3. Test connection (paste in Cursor)
"List available n8n nodes. use context7"
```

---

## 📚 Document Quick Links

| Need | Read | Time |
|------|------|------|
| **First workflow** | [Quick Start](N8N_QUICK_START.md) | 5 min |
| **Any workflow** | [Workflow Prompt](N8N_WORKFLOW_CREATION_PROMPT.md) | 2 min |
| **External APIs** | [Context7 Guide](CONTEXT7_N8N_INTEGRATION_GUIDE.md) | 5 min |
| **Errors** | [Validation Protocol](N8N_NODE_VALIDATION_PROTOCOL.md) | 3 min |
| **System overview** | [Setup Summary](N8N_MCP_COMPLETE_SETUP_SUMMARY.md) | 10 min |

---

## ⚡ Common Prompts

### 1. Simple Data Pipeline
```
Create n8n workflow:
- Webhook receives data
- Validate JSON
- Store in PostgreSQL
- Send Slack notification

Follow N8N_WORKFLOW_CREATION_PROMPT.md process
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

## 🔧 Troubleshooting Fast Fixes

| Problem | Fix |
|---------|-----|
| **Red dot in MCP settings** | Restart Cursor |
| **Context7 not working** | Add `use context7` to prompt |
| **401 API errors** | Use Context7 for current auth |
| **Deprecated parameters** | Add `use context7` to prompt |
| **Wrong typeVersion** | Let n8n-mcp validate |

**Full troubleshooting:** [Validation Protocol](N8N_NODE_VALIDATION_PROTOCOL.md#troubleshooting)

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

**Full guide:** [Context7 Integration](CONTEXT7_N8N_INTEGRATION_GUIDE.md#when-to-use)

---

## 📊 The 5-Phase Process

```
┌─────────────────────────────────────┐
│ Phase 0: Template Search            │
│ Find existing patterns              │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Phase 1: Node Discovery             │
│ Identify exact nodes needed         │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Phase 2: Essential Properties       │
│ Get required configurations         │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Phase 3: Documentation Review       │
│ n8n-mcp docs + Context7 current API │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Phase 4: Workflow Construction      │
│ Build JSON with validation          │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Phase 5: Pre-Deployment Validation  │
│ Final checks                        │
└─────────────────────────────────────┘
              ↓
        ✅ Perfect Workflow
```

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
   ↓
2. Login to https://ibeylin.app.n8n.cloud
   ↓
3. Click "+ Add workflow"
   ↓
4. Click ⋮ menu → "Import from File"
   ↓
5. Select JSON file
   ↓
6. Configure credentials
   ↓
7. Click "Test workflow"
   ↓
8. Verify output
   ↓
9. Click "Save" → "Activate"
```

**Full tutorial:** [Workflow Prompt](N8N_WORKFLOW_CREATION_PROMPT.md#deployment-tutorial)

---

## 🎯 Common Use Cases at a Glance

### BCP Intelligence Pipeline
```
Webhook → Perplexity API → PostgreSQL → Neo4j → Slack
Guide: CONTEXT7_N8N_INTEGRATION_GUIDE.md Use Case 3
```

### Data Validation Pipeline
```
Webhook → Validate JSON → PostgreSQL → Slack
Guide: N8N_QUICK_START.md
```

### API Integration
```
Trigger → HTTP Request (current API) → Process → Store
Guide: CONTEXT7_N8N_INTEGRATION_GUIDE.md Example 1
```

### Legacy Update
```
Old Workflow → Analyze → Update versions → Modernize auth
Guide: CONTEXT7_N8N_INTEGRATION_GUIDE.md Use Case 1
```

---

## 📞 Quick Help

| Issue | Where to Look |
|-------|---------------|
| **Setup issues** | [Quick Start](N8N_QUICK_START.md) |
| **Validation errors** | [Validation Protocol](N8N_NODE_VALIDATION_PROTOCOL.md) |
| **API errors** | [Context7 Guide](CONTEXT7_N8N_INTEGRATION_GUIDE.md) |
| **How-to questions** | [Workflow Prompt](N8N_WORKFLOW_CREATION_PROMPT.md) |
| **System understanding** | [Architecture](N8N_MCP_SYSTEM_ARCHITECTURE.md) |

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
Follow N8N_WORKFLOW_CREATION_PROMPT.md 5-phase process.
use context7
```

**Replace [DESCRIBE YOUR AUTOMATION] with your use case.**

---

**Print this page** | Keep it next to your keyboard | Build perfect workflows 🚀

---

**Version:** 1.0
**Last Updated:** 2025-11-09
**Full Docs:** [README.md](README.md)
