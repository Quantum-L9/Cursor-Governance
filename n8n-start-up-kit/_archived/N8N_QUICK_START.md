# n8n Workflow Creation - 5-Minute Quick Start

**Goal:** Get a working n8n workflow in 5 minutes

---

## 📚 Document Suite Overview

This is part of the **n8n MCP Documentation Suite**:

| Document | Purpose |
|----------|---------|
| **[N8N_QUICK_START.md](N8N_QUICK_START.md)** | 5-minute quick start ← **YOU ARE HERE** |
| **[N8N_WORKFLOW_CREATION_PROMPT.md](N8N_WORKFLOW_CREATION_PROMPT.md)** | AI prompt template for complex workflows |
| **[CONTEXT7_N8N_INTEGRATION_GUIDE.md](CONTEXT7_N8N_INTEGRATION_GUIDE.md)** | Context7 integration for up-to-date docs |
| **[N8N_NODE_VALIDATION_PROTOCOL.md](N8N_NODE_VALIDATION_PROTOCOL.md)** | Complete reference guide |

---

## Step 1: Setup (30 seconds)

```bash
# Install n8n-mcp
npx -y n8n-mcp

# Set your credentials (get from n8n Settings → API)
export N8N_API_KEY="your-api-key-here"
export N8N_URL="https://your-instance.app.n8n.cloud"
```

**Don't have an API key?** See [How to Get Your n8n API Key](N8N_WORKFLOW_CREATION_PROMPT.md#-how-to-get-your-n8n-api-key)

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

1. **Read:** [N8N_WORKFLOW_CREATION_PROMPT.md](N8N_WORKFLOW_CREATION_PROMPT.md)
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

Follow the 5-phase validation process from N8N_WORKFLOW_CREATION_PROMPT.md

use context7
```

**Why `use context7`?** This adds up-to-date n8n documentation to ensure current node configurations and no deprecated code. See [CONTEXT7_N8N_INTEGRATION_GUIDE.md](CONTEXT7_N8N_INTEGRATION_GUIDE.md) for details.

### Deep Dive into n8n

- **Context7 Integration:** [CONTEXT7_N8N_INTEGRATION_GUIDE.md](CONTEXT7_N8N_INTEGRATION_GUIDE.md)
- **Reference Guide:** [N8N_NODE_VALIDATION_PROTOCOL.md](N8N_NODE_VALIDATION_PROTOCOL.md)
- **Gap Analysis:** [N8N_PROTOCOL_GAP_ANALYSIS.md](N8N_PROTOCOL_GAP_ANALYSIS.md)
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
