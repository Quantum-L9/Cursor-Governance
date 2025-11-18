---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-N8N-006"
component_name: "n8n Quick Start Guide"
layer: "intelligence"
domain: "n8n_automation"
type: "documentation"
status: "active"
created: "2025-01-27T00:00:00Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "medium"
compliance_required: true
audit_trail: false
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["INT-N8N-001"]
integrates_with: ["INT-N8N-002"]
api_endpoints: []
data_sources: []
outputs: ["example_workflows"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: false
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "5-minute quick start guide for creating first n8n workflow"
summary: "Working Hello World example with step-by-step import instructions"
business_value: "Enables rapid first workflow creation and system validation"
success_metrics: ["first_workflow_time < 5min", "import_success_rate >= 0.95"]

# === TAGS & CLASSIFICATION ===
tags: ["n8n", "workflow", "quick-start", "tutorial"]
keywords: ["n8n", "workflow", "quick-start", "example", "hello-world"]
related_components: ["INT-N8N-001", "INT-N8N-002"]
startup_required: false
mode_type: "documentation"
---

# n8n Workflow Creation - 5-Minute Quick Start

**Goal:** Get a working n8n workflow in 5 minutes

---

## 📚 Document Suite Overview

This is part of the **n8n MCP Documentation Suite**:

| Document | Purpose |
|----------|---------|
| **[06_QUICK_START.md](06_QUICK_START.md)** | 5-minute quick start ← **YOU ARE HERE** |
| **[02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md)** | AI prompt template for complex workflows |
| **[03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md)** | Context7 integration for up-to-date docs |
| **[04_VALIDATION_PROTOCOL.md](04_VALIDATION_PROTOCOL.md)** | Complete reference guide |

---

## Step 1: Setup (30 seconds)

```bash
# Install n8n-mcp
npx -y n8n-mcp

# Set your credentials (get from n8n Settings → API)
export N8N_API_KEY="your-api-key-here"
export N8N_URL="https://your-instance.app.n8n.cloud"
```

**Don't have an API key?** See [How to Get Your n8n API Key](02_WORKFLOW_CREATION.md#-how-to-get-your-n8n-api-key)

---

## Step 2: Copy This Working Workflow (1 minute)

**Save as `simple-workflow.json`:**

```json
{
  "name": "Hello World Workflow",
  "nodes": [
    {
      "parameters": {},
      "id": "start-node",
      "name": "When clicking 'Test workflow'",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "values": {
          "string": [
            {
              "name": "message",
              "value": "Hello from n8n!"
            }
          ]
        }
      },
      "id": "set-message",
      "name": "Set Message",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.3,
      "position": [450, 300]
    }
  ],
  "connections": {
    "When clicking 'Test workflow'": {
      "main": [[{"node": "Set Message", "type": "main", "index": 0}]]
    }
  },
  "active": false,
  "settings": {},
  "tags": []
}
```

---

## Step 3: Import to n8n (2 minutes)

1. **Login to your n8n instance**
   - Cloud: https://[your-instance].app.n8n.cloud
   - Self-hosted: http://localhost:5678

2. **Create new workflow**
   - Click "+ Add workflow" (top-right corner)

3. **Import the JSON**
   - Click the "⋮" menu (three dots, top-right)
   - Select "Import from File"
   - Choose your `simple-workflow.json` file
   - Click "Open"

4. **Test it!**
   - Click "Test workflow" button
   - See "Hello from n8n!" in the output panel

---

## Step 4: Modify and Experiment (2 minutes)

Change the message:

1. Click "Set Message" node
2. Change "Hello from n8n!" to your text
3. Click "Test workflow" again
4. See your custom message!

---

## ✅ Success!

You now have a working n8n workflow.

---

## 🚀 Next Steps

### Learn to Build Complex Workflows

Use the AI-powered workflow creation prompt:

1. **Read:** [02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md)
2. **Copy the prompt template** from Phase 0-5
3. **Paste into Cursor/Claude** with your workflow requirements
4. **AI generates** validated, production-ready workflows

### Example Request to AI:

```
Using the n8n MCP, create a workflow that:
- Triggers on webhook POST to /data-intake
- Validates incoming JSON has required fields
- Sends data to external API
- Logs success to Google Sheets
- Sends Slack notification on error

Follow the 5-phase validation process from 02_WORKFLOW_CREATION.md

use context7
```

**Why `use context7`?** This adds up-to-date n8n documentation to ensure current node configurations and no deprecated code. See [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md) for details.

### Deep Dive into n8n

- **Context7 Integration:** [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md)
- **Reference Guide:** [04_VALIDATION_PROTOCOL.md](04_VALIDATION_PROTOCOL.md)
- **System Architecture:** [05_SYSTEM_ARCHITECTURE.md](05_SYSTEM_ARCHITECTURE.md)
- **Official Docs:** https://docs.n8n.io

---

## 🔧 Troubleshooting

### Import Failed?
- **Check JSON syntax:** Use jsonlint.com to validate
- **Ensure complete copy:** No truncation in JSON

### Can't find Import option?
- **Location:** Click ⋮ (three dots) → "Import from File"
- **Alternative:** Settings → Import Workflow

### Workflow won't execute?
- **Manual trigger:** Click "Test workflow" button
- **Check credentials:** If using API nodes, configure credentials first

---

## 📞 Need Help?

- **n8n Community Forum:** https://community.n8n.io
- **n8n Discord:** https://discord.gg/n8n
- **Documentation Suite:** Read the other guides in this folder

---

**Version:** 1.0
**Last Updated:** 2025-11-09
**Time to Complete:** ~5 minutes
