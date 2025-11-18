# n8n Node Validation Protocol for AI Assistants

## Table of Contents
1. [Overview](#overview)
2. [Important: Two Different MCP Servers](#-important-two-different-mcp-servers)
3. [Troubleshooting](#-troubleshooting-mcp-connection-issues)
4. [Pre-Implementation Validation Workflow](#-pre-implementation-validation-workflow)
5. [Complete MCP Tool Reference](#-complete-n8n-mcp-tool-reference)
6. [Validation Checklist](#-validation-checklist-for-ai-assistants)
7. [Implementation Pattern](#-implementation-pattern)
8. [Common Errors](#-common-validation-errors-to-avoid)
9. [Best Practices](#-best-practices-for-ai-assistants)
10. [Quick Reference](#-quick-reference-template-search-commands)
11. [Configuration Examples](#-configuration-examples)
12. [Key Takeaways](#-key-takeaways)

---

## Overview
This protocol ensures that AI assistants (Claude, Cursor, etc.) validate n8n nodes against the actual n8n MCP server before implementing workflows, guaranteeing correct node versions, configurations, and property setups.

---

## 🚨 IMPORTANT: Two Different MCP Servers

**CRITICAL DISTINCTION:** There are THREE MCP servers that work together for n8n workflow creation:

### Server Type A: n8n-mcp (Node Documentation Server)
**Purpose:** Query node schemas, properties, and documentation
**Repository:** [czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp)
**Installation:** `npx -y n8n-mcp`

**Tools Provided:**
- `search_nodes` - Search for nodes by name/functionality
- `list_nodes` - Browse nodes by category
- `list_ai_tools` - List AI-capable nodes (271 available)
- `get_node_essentials` - Get essential properties (10-20 instead of 200+)
- `get_node_documentation` - Get human-readable docs
- `search_node_properties` - Find specific properties
- `validate_workflow` - Validate complete workflow JSON

**Configuration:**
```json
"n8n-mcp-docs": {
  "command": "npx",
  "args": ["-y", "n8n-mcp"],
  "env": {
    "N8N_API_KEY": "your-api-key-here",
    "N8N_URL": "https://ibeylin.app.n8n.cloud"
  }
}
```

### Server Type B: n8n Instance MCP Server (Workflow Management)
**Purpose:** Manage workflows, executions, credentials in your n8n instance
**Access:** Via webhook endpoint or n8n REST API
**Your Setup:** Remote webhook at `https://ibeylin.app.n8n.cloud/mcp/...`

**Tools Provided (33 total):**
- Workflow Management: `create-workflow`, `update-workflow`, `list-workflows`, etc.
- Execution Management: `list-executions`, `get-execution`, etc.
- Credential Management: `create-credential`, `get-credential-schema`, etc.
- Organization: Tags, variables, projects, users
- Security: `generate-audit`

**Configuration:**
```json
"n8n-instance": {
  "command": "npx",
  "args": [
    "-y", "mcp-remote",
    "https://ibeylin.app.n8n.cloud/mcp/5786107c-c7a6-46d2-91d4-a68ba1756308",
    "--header", "Authorization: Bearer YOUR_TOKEN"
  ]
}
```

### Recommended Setup: Use BOTH Servers
```json
{
  "mcpServers": {
    "n8n-docs": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "N8N_API_KEY": "your-api-key",
        "N8N_URL": "https://ibeylin.app.n8n.cloud"
      }
    },
    "n8n-instance": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "https://ibeylin.app.n8n.cloud/mcp/YOUR-WEBHOOK-ID",
        "--header", "Authorization: Bearer YOUR_TOKEN"
      ]
    }
  }
}
```

---

### Server Type C: Context7 MCP (Up-to-Date Documentation Server)
**Purpose:** Provide current, version-specific documentation for n8n and external APIs
**Repository:** [upstash/context7](https://github.com/upstash/context7)
**Installation:** Already configured at `https://mcp.context7.com/mcp`

**What It Provides:**
- Current n8n documentation (eliminates outdated AI training data)
- Latest external API specifications (Slack, Google Sheets, etc.)
- Version-specific code examples
- Up-to-date authentication patterns
- Deprecated parameter warnings

**Configuration:**
```json
"Context7": {
  "url": "https://mcp.context7.com/mcp",
  "headers": {
    "CONTEXT7_API_KEY": "optional-but-recommended"
  }
}
```

**Usage Pattern:**
Add `use context7` to any prompt to fetch current documentation

**Learn More:** See [CONTEXT7_N8N_INTEGRATION_GUIDE.md](CONTEXT7_N8N_INTEGRATION_GUIDE.md) for complete integration patterns

---

### Recommended Setup: Use All Three Servers

**Why use all three?**
1. **n8n-mcp (Type A)**: Provides node structure and schemas
2. **n8n Instance MCP (Type B)**: Manages your actual workflows
3. **Context7 (Type C)**: Ensures current documentation and no deprecated code

**Complete Configuration:**
```json
{
  "mcpServers": {
    "n8n-docs": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "N8N_API_KEY": "your-n8n-api-key",
        "N8N_URL": "https://ibeylin.app.n8n.cloud"
      }
    },
    "Context7": {
      "url": "https://mcp.context7.com/mcp",
      "headers": {
        "CONTEXT7_API_KEY": "your-context7-api-key"
      }
    }
  }
}
```

---

## 🚨 TROUBLESHOOTING: MCP Connection Issues

### Red Dot / Error in Cursor Settings?

**Problem:** n8n MCP showing error in `~/.cursor/mcp.json` with red indicator

**Root Cause:** The n8n workflow with the webhook endpoint **is not active** in your n8n instance.

**Error Message:**
```
HTTP 404: The requested webhook "POST 5786107c-c7a6-46d2-91d4-a68ba1756308" is not registered.
Hint: The workflow must be active for a production URL to run successfully.
```

**Solution:**

1. **Login to n8n:** [https://ibeylin.app.n8n.cloud](https://ibeylin.app.n8n.cloud)

2. **Find the MCP Workflow:**
   - Look for workflow with webhook ID: `5786107c-c7a6-46d2-91d4-a68ba1756308`
   - OR create a new workflow with MCP Server capabilities

3. **Activate the Workflow:**
   - Click the toggle switch in top-right corner of editor
   - Ensure it shows as "Active" (green)

4. **Verify Connection:**
   ```bash
   curl -X POST https://ibeylin.app.n8n.cloud/mcp/5786107c-c7a6-46d2-91d4-a68ba1756308 \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```
   Should return workflow response, not 404 error

5. **Restart Cursor/Claude Code** to reconnect to the MCP server

**Alternative:** If you don't have this workflow, you may need to:
- Install the n8n-mcp server locally using `npx -y n8n-mcp` instead
- Or update the webhook URL to a different n8n MCP endpoint

---

## 🎯 Pre-Implementation Validation Workflow

### Phase 1: Node Discovery & Validation

Before creating or modifying any n8n workflow, follow this validation sequence:

#### Step 1: Search & Identify Nodes
```
BEFORE: Planning to use "HTTP Request" node
ACTION: Use MCP tool → search_nodes
QUERY: "HTTP Request"
VALIDATE: Confirm exact node name and availability
```

**Available MCP Tools for Node Discovery:**
- `search_nodes` - Full-text search across all node documentation
- `list_nodes` - Browse by category (trigger, action, etc.)
- `list_ai_tools` - List all AI-capable nodes (271 available)

#### Step 2: Get Essential Properties
```
BEFORE: Configuring node properties
ACTION: Use MCP tool → get_node_essentials
TARGET: Specific node name (e.g., "n8n-nodes-base.httpRequest")
RESULT: Receive 10-20 essential properties instead of 200+
```

**What You Get:**
- Required properties only
- Property types and constraints
- Default values
- Validation rules

#### Step 3: Retrieve Full Documentation
```
BEFORE: Implementing node logic
ACTION: Use MCP tool → get_node_documentation
TARGET: Node name
RESULT: Human-readable documentation with examples
```

#### Step 4: Search Specific Properties
```
BEFORE: Configuring complex properties
ACTION: Use MCP tool → search_node_properties
QUERY: Property name or keyword
RESULT: Property schemas and valid options
```

#### Step 5: Validate Configuration
```
BEFORE: Adding node to workflow
ACTION: Use MCP tool → validate
INPUT: Node configuration JSON
RESULT: Validation errors or success confirmation
```

---

## 🔧 Complete n8n MCP Tool Reference

### 📚 Node Information Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `search_nodes` | Full-text search across nodes | Finding nodes by functionality |
| `list_nodes` | Browse nodes by category | Exploring available triggers/actions |
| `list_ai_tools` | List AI-capable nodes | Building AI agent workflows |
| `get_node_essentials` | Get essential properties (10-20) | Quick node configuration |
| `get_node_documentation` | Full human-readable docs | Understanding node behavior |
| `search_node_properties` | Find specific properties | Looking for specific configs |

### ✅ Validation Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `validate` | Validate node configurations | Before adding nodes to workflow |
| AI Workflow Validation | Comprehensive AI workflow check | Before deploying AI agent workflows |

### 🔄 Workflow Management Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `init-n8n` | Initialize n8n connection | URL, API key |
| `list-workflows` | Display all workflows | Filter options |
| `get-workflow` | Retrieve workflow details | Workflow ID |
| `create-workflow` | Build new workflow | Workflow JSON |
| `update-workflow` | Modify existing workflow | Workflow ID, changes |
| `delete-workflow` | Remove workflow | Workflow ID |
| `activate-workflow` | Enable workflow | Workflow ID |
| `deactivate-workflow` | Disable workflow | Workflow ID |

### 📊 Execution Tools

| Tool | Purpose |
|------|---------|
| `list-executions` | View execution history |
| `get-execution` | Get execution details |
| `delete-execution` | Remove execution record |

### 🔐 Credential Tools

| Tool | Purpose |
|------|---------|
| `get-credential-schema` | Get credential requirements |
| `create-credential` | Add new credential |
| `delete-credential` | Remove credential |

### 🏷️ Organization Tools

| Tool | Purpose |
|------|---------|
| `list-tags` / `create-tag` / `update-tag` / `delete-tag` | Manage tags |
| `get-workflow-tags` / `update-workflow-tags` | Manage workflow tags |
| `list-variables` / `create-variable` / `delete-variable` | Manage variables (Enterprise) |
| `list-projects` / `create-project` / `update-project` / `delete-project` | Manage projects (Enterprise) |

### 👥 User Management Tools

| Tool | Purpose |
|------|---------|
| `list-users` / `get-user` / `create-users` / `delete-user` | Manage users |

### 🔒 Security Tools

| Tool | Purpose |
|------|---------|
| `generate-audit` | Generate security audit report |

---

## 📋 Validation Checklist for AI Assistants

### Before Creating Any n8n Workflow:

- [ ] **Step 0:** **SEARCH TEMPLATES FIRST** - Use `search_workflows` or `list_workflows` to find similar existing patterns from 2,646 pre-built templates
- [ ] **Step 1:** Use `search_nodes` to confirm node exists
- [ ] **Step 2:** Use `get_node_essentials` to understand required properties
- [ ] **Step 3:** Use `get_node_documentation` to review usage examples
- [ ] **Step 4:** Use `search_node_properties` for complex configurations
- [ ] **Step 5:** Use `validate` to check node configuration before implementation
- [ ] **Step 6:** Check for AI Workflow Validation if using AI agent nodes
- [ ] **Step 7:** If template found, use `get-workflow` to retrieve complete configuration
- [ ] **Step 8:** Verify all connections between nodes are valid
- [ ] **Step 9:** Ensure workflow has more than one node (unless webhook)
- [ ] **Step 10:** Test configuration before deployment

---

## 🚀 Implementation Pattern

### Example: Creating an HTTP Request Workflow

```markdown
## Phase 0: SEARCH TEMPLATES FIRST (ALWAYS START HERE)

0. **Search Existing Templates:**
   - Tool: `list-workflows` or `search_workflows`
   - Query: Keywords like "HTTP", "API", "webhook"
   - Result: Check if similar workflow already exists in 2,646 templates

   If found:
   - Tool: `get-workflow`
   - Input: Template workflow ID
   - Result: Use as starting point, modify as needed

## Phase 1: Validation (REQUIRED BEFORE CODING)

1. **Search Node:**
   - Tool: `search_nodes`
   - Query: "HTTP Request"
   - Result: Confirm "n8n-nodes-base.httpRequest" is available

2. **Get Essentials:**
   - Tool: `get_node_essentials`
   - Node: "n8n-nodes-base.httpRequest"
   - Result: Review essential properties:
     * url (string, required)
     * method (enum: GET/POST/PUT/DELETE, required)
     * authentication (enum: none/basicAuth/oauth2, optional)
     * options (object, optional)

3. **Get Documentation:**
   - Tool: `get_node_documentation`
   - Node: "n8n-nodes-base.httpRequest"
   - Result: Review examples and best practices

4. **Search Properties:**
   - Tool: `search_node_properties`
   - Query: "authentication"
   - Result: Understand authentication options

## Phase 2: Configuration

5. **Create Configuration:**
```json
{
  "name": "HTTP Request",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "url": "https://api.example.com/data",
    "method": "GET",
    "authentication": "none"
  }
}
```

## Phase 3: Validation

6. **Validate Configuration:**
   - Tool: `validate`
   - Input: Above JSON
   - Result: Check for errors

## Phase 4: Implementation

7. **Create Workflow:**
   - Tool: `create-workflow`
   - Input: Complete workflow JSON
   - Result: Workflow ID

8. **Activate:**
   - Tool: `activate-workflow`
   - Input: Workflow ID
```

---

## ⚠️ Common Validation Errors to Avoid

### 1. Wrong Node Name
```
❌ BAD: "HTTP" or "HTTPRequest"
✅ GOOD: "n8n-nodes-base.httpRequest"
```

### 2. Missing Required Properties
```
❌ BAD: Only providing URL without method
✅ GOOD: Validate all required properties first
```

### 3. Invalid Property Values
```
❌ BAD: method: "FETCH"
✅ GOOD: method: "GET" (validated from essentials)
```

### 4. Using Deprecated Properties
```
❌ BAD: Using outdated property names
✅ GOOD: Check get_node_essentials for current schema
```

### 5. Single-Node Workflows (Non-Webhook)
```
❌ BAD: Workflow with one action node
✅ GOOD: Multi-node workflow with proper connections
```

---

## 🎓 Best Practices for AI Assistants

### 1. Always Validate First
**NEVER** assume node names, properties, or configurations. Always query the MCP server first.

### 2. Use Essential Properties
Instead of guessing from a 100KB schema, use `get_node_essentials` to get the 10-20 properties that matter.

### 3. Search Templates FIRST
**ALWAYS START BY SEARCHING TEMPLATES** before building from scratch:
- Use `list-workflows` to browse available templates
- Use `get-workflow` to retrieve specific template configurations
- Modify existing templates instead of creating from scratch
- 2,646 pre-extracted templates cover most common use cases

### 4. Validate Early, Validate Often
- Validate individual nodes before adding to workflow
- Validate complete workflow before deployment
- Run AI Workflow Validation for AI agent workflows

### 5. Document Your Validation Steps
When creating workflows, show the user:
- Which nodes you validated
- What properties you confirmed
- Any validation errors encountered
- How you resolved configuration issues

---

## 🎯 QUICK REFERENCE: Template Search Commands

### How to Search Templates (Step 0 - ALWAYS DO FIRST)

```markdown
BEFORE building any workflow:

1. List all available workflows:
   Tool: list-workflows
   Result: Browse 2,646 pre-built templates

2. Get specific workflow details:
   Tool: get-workflow
   Input: {workflow_id}
   Result: Complete workflow JSON configuration

3. Search by keyword (if available):
   Tool: search_workflows (check if available)
   Query: "HTTP", "Slack", "webhook", etc.

4. Use retrieved template as starting point:
   - Copy template configuration
   - Modify for your specific needs
   - Validate changes with validate tool
```

**Why Templates First?**
- Saves 80-90% development time
- Pre-validated configurations
- Best practices already implemented
- Reduces errors and token usage

---

## 📋 Configuration Examples

### Example 1: Complete Workflow JSON Structure

```json
{
  "name": "HTTP to Slack Notification",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "webhook",
        "responseMode": "onReceived"
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [250, 300],
      "webhookId": "unique-webhook-id"
    },
    {
      "parameters": {
        "url": "https://api.example.com/data",
        "authentication": "none",
        "method": "GET"
      },
      "name": "HTTP Request",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [450, 300]
    },
    {
      "parameters": {
        "channel": "#general",
        "text": "=Data received: {{$json[\"data\"]}}"
      },
      "name": "Slack",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 1,
      "position": [650, 300],
      "credentials": {
        "slackApi": {
          "id": "1",
          "name": "Slack account"
        }
      }
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "HTTP Request", "type": "main", "index": 0}]]
    },
    "HTTP Request": {
      "main": [[{"node": "Slack", "type": "main", "index": 0}]]
    }
  },
  "active": false,
  "settings": {},
  "tags": []
}
```

### Example 2: Credential Creation Workflow

```markdown
1. Get credential schema:
   Tool: get-credential-schema
   Input: {credential_type: "slackApi"}

2. Create credential:
   Tool: create-credential
   Input: {
     "name": "Slack account",
     "type": "slackApi",
     "data": {
       "token": "xoxb-your-token-here"
     }
   }

3. Reference credential in node:
   "credentials": {
     "slackApi": {
       "id": "1",
       "name": "Slack account"
     }
   }
```

### Example 3: Connection/Edge Validation

```markdown
Validate all connections have:
1. Source node exists
2. Target node exists
3. Valid connection type (main, error, etc.)
4. Valid index numbers
5. No circular dependencies

Example validation check:
"connections": {
  "Node A": {
    "main": [[{"node": "Node B", "type": "main", "index": 0}]]
  }
}

✅ VALID: Node B exists in workflow
❌ INVALID: Node B not found in nodes array
```

### Example 4: Error Handling Strategy

```markdown
When validation fails:

1. Capture error message
2. Identify error type:
   - Missing required property
   - Invalid property value
   - Wrong node name
   - Missing connection
   - Credential issue

3. Query MCP for correction:
   - Use get_node_essentials to review requirements
   - Use search_node_properties for valid values
   - Use get-credential-schema for credential fields

4. Retry validation
5. Document resolution for user
```

### Example 5: Batch Workflow Creation

```markdown
For multiple similar workflows:

1. Create template workflow first
2. Validate template
3. Clone and modify for each instance
4. Use update-workflow for modifications
5. Batch activate with activate-workflow

Rate limiting:
- Max 10 workflows/minute
- Add 6-second delay between creates
- Use init-n8n once, reuse connection
```

---

## 🔗 Integration with Your MCP Configuration

### Current Setup Analysis

Your current n8n MCP setup at `~/.cursor/mcp.json` (lines 56-65):

```json
"n8n": {
  "command": "npx",
  "args": [
    "-y",
    "mcp-remote",
    "https://ibeylin.app.n8n.cloud/mcp/5786107c-c7a6-46d2-91d4-a68ba1756308",
    "--header",
    "Authorization: Bearer [TOKEN]"
  ]
}
```

**Status:** ⚠️ Webhook not registered (workflow needs activation)

**Once Active, You'll Have Access To:**
- 541 n8n nodes with 99% property coverage
- 2,646 pre-extracted workflow templates
- All 33 MCP tools listed above
- Real-time validation with 12ms response time

---

## 📝 Prompt Template for AI Assistants

When asked to create n8n workflows, use this template:

```
I'll create this n8n workflow following the validation protocol:

0. TEMPLATE SEARCH (ALWAYS START HERE):
   - Searching existing workflows for similar patterns...
   - Tool: list-workflows / get-workflow
   - [Show search results and whether template found]

1. NODE DISCOVERY:
   - Searching for required nodes...
   - [List search results]

2. NODE VALIDATION:
   - Getting essential properties for [NodeName]...
   - Required properties: [List]
   - Optional properties: [List]

3. CONFIGURATION:
   - Creating node configuration...
   - [Show JSON]

4. VALIDATION:
   - Validating configuration...
   - [Show validation results]

5. IMPLEMENTATION:
   - Creating workflow...
   - [Show result]

Would you like me to proceed with this validated configuration?
```

---

## 🎯 Key Takeaways

1. **Never Skip Validation** - Always query MCP server before implementation
2. **Use the Right Tools** - Leverage specialized MCP tools for each task
3. **Start with Essentials** - Use `get_node_essentials` not full schema dumps
4. **Validate Configurations** - Check every node config before adding to workflow
5. **Reference Templates** - Check 2,646 examples before building from scratch
6. **Document Process** - Show validation steps to users for transparency

---

## 📚 Additional Resources

- **n8n Node Count:** 541 nodes (n8n-nodes-base + @n8n/n8n-nodes-langchain)
- **Property Coverage:** 99% of all node properties documented
- **AI-Capable Nodes:** 271 nodes with full AI documentation
- **Pre-built Templates:** 2,646 workflow configurations
- **Average Query Time:** 12ms (SQLite-powered)

---

---

## 📊 Version Compatibility Matrix

| n8n-mcp Version | Features | Status |
|----------------|----------|--------|
| **v2.17.0+** | AI Workflow Validation, 541 nodes, 271 AI nodes | ✅ Recommended |
| **v2.16.x** | 525+ nodes, validation tools | ✅ Supported |
| **v2.15.x** | Basic node queries, templates | ⚠️ Limited |
| **< v2.15** | Legacy support only | ❌ Not recommended |

### Feature Availability by Version

| Feature | v2.15 | v2.16 | v2.17+ |
|---------|-------|-------|--------|
| search_nodes | ✅ | ✅ | ✅ |
| get_node_essentials | ✅ | ✅ | ✅ |
| validate_workflow | ❌ | ✅ | ✅ |
| AI Workflow Validation | ❌ | ❌ | ✅ |
| 2,646 templates | ❌ | ✅ | ✅ |
| 12ms query time | ❌ | ❌ | ✅ |

---

## 🛡️ Security and Rate Limiting

### API Key Management
```bash
# Set environment variables (recommended)
export N8N_API_KEY="your-api-key-here"
export N8N_URL="https://ibeylin.app.n8n.cloud"

# Never commit API keys to version control
echo "N8N_API_KEY=*" >> .gitignore
```

### Rate Limits (n8n Cloud)
- **Workflow Creates:** 10/minute
- **Workflow Updates:** 20/minute
- **Executions:** 100/minute
- **List Operations:** 60/minute

### Best Practices
1. Cache node documentation locally
2. Batch workflow operations
3. Use webhooks for high-frequency triggers
4. Implement exponential backoff on failures
5. Monitor API usage with `generate-audit`

---

## 🔄 Migration Guide

### Migrating from Remote Webhook to Local MCP

**Step 1:** Install n8n-mcp locally
```bash
npx -y n8n-mcp
```

**Step 2:** Update mcp.json
```json
{
  "mcpServers": {
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

**Step 3:** Restart Cursor/Claude Code

**Step 4:** Verify connection
```bash
# Should return node list
curl localhost:3000/mcp/list_nodes
```

---

## 📖 Glossary

| Term | Definition |
|------|------------|
| **Node** | A single operation/action in an n8n workflow (HTTP Request, Slack, etc.) |
| **Workflow** | Complete automation consisting of connected nodes |
| **Execution** | A single run of a workflow with input data |
| **Credential** | Stored authentication info for external services |
| **Webhook** | HTTP endpoint that triggers workflow execution |
| **Connection/Edge** | Link between nodes defining data flow |
| **MCP** | Model Context Protocol - standard for AI tool integration |
| **Template** | Pre-built workflow configuration |
| **Validation** | Checking workflow/node config for errors before deployment |

---

## 📞 Support and Resources

### Official Documentation
- [n8n Documentation](https://docs.n8n.io)
- [n8n-mcp GitHub](https://github.com/czlonkowski/n8n-mcp)
- [MCP Protocol Spec](https://modelcontextprotocol.io)

### Community
- [n8n Community Forum](https://community.n8n.io)
- [n8n Discord](https://discord.gg/n8n)

### Troubleshooting
- Red dot in Cursor: See [Troubleshooting section](#-troubleshooting-mcp-connection-issues)
- Node not found: Use `search_nodes` to verify name
- Validation errors: Check `get_node_essentials` for requirements
- Connection issues: Verify n8n instance is running and API key is valid

---

**Last Updated:** 2025-11-09
**Protocol Version:** 2.0
**Compatible with:** n8n-mcp v2.17.0+, n8n Cloud/Self-hosted v1.0+
**Maintained by:** Igor Beylin
