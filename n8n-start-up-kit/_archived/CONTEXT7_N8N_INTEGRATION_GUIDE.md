# Context7 + n8n MCP Integration Guide

**Purpose:** Leverage Context7 MCP alongside n8n-mcp for up-to-date documentation during workflow creation

**Date:** 2025-11-09
**Version:** 1.0
**Status:** Production Ready

---

## 📚 What is Context7 MCP?

Context7 is an MCP server that **eliminates API hallucination** by providing:

- **Up-to-date, version-specific documentation** directly in your AI prompt
- **Real code examples** from source repositories
- **No outdated APIs** or deprecated patterns
- **No tab-switching** required

**Key Benefit:** Context7 fetches current documentation while n8n-mcp provides node schemas - together they ensure both **accurate n8n workflows** and **correct API usage**.

---

## 🔄 How Context7 Complements n8n-mcp

### The Two-Server Strategy

| Server | Purpose | What It Provides |
|--------|---------|------------------|
| **n8n-mcp** | n8n-specific workflow management | Node schemas, workflow CRUD, execution monitoring |
| **Context7** | Up-to-date documentation | Current n8n APIs, latest node documentation, version-specific features |

**Why Use Both?**

1. **n8n-mcp** tells you WHAT nodes exist and HOW to configure them (structure)
2. **Context7** tells you CURRENT documentation for those nodes (content)
3. Together = No broken workflows + No outdated code

---

## ⚙️ Configuration

### Your Current Setup

You already have Context7 configured! Your [mcp.json](~/.cursor/mcp.json#L21-L24):

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
    },
    "n8n": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "N8N_API_KEY": "your-n8n-api-key",
        "N8N_URL": "https://ibeylin.app.n8n.cloud"
      }
    }
  }
}
```

**Benefits of API Key:**
- Higher rate limits
- Access to private documentation
- Priority support

---

## 🚀 Usage Pattern: The Enhanced Workflow

### Standard n8n Workflow Prompt (Without Context7)

```
Create an n8n workflow that:
- Triggers on webhook POST to /data-intake
- Validates incoming JSON
- Sends data to external API
- Logs to Google Sheets

Follow the 5-phase validation process from N8N_WORKFLOW_CREATION_PROMPT.md
```

### Enhanced Prompt (With Context7)

```
Create an n8n workflow that:
- Triggers on webhook POST to /data-intake
- Validates incoming JSON
- Sends data to external API
- Logs to Google Sheets

Follow the 5-phase validation process from N8N_WORKFLOW_CREATION_PROMPT.md

use context7
```

**What Changes:**
- Adding `use context7` triggers real-time documentation lookup
- AI receives current n8n API documentation
- Ensures latest node configurations and parameters
- Eliminates deprecated code patterns

---

## 📖 Practical Examples

### Example 1: Creating HTTP Request Node with Current API

**Prompt:**
```
Using n8n-mcp, create an HTTP Request node that:
- Makes POST request to https://api.example.com/data
- Includes JWT authentication header
- Handles 429 rate limit errors with retry logic
- Returns parsed JSON response

Ensure all parameters match the latest n8n HTTP Request node API. use context7
```

**What Happens:**

1. **n8n-mcp provides:**
   - Node schema for `n8n-nodes-base.httpRequest`
   - Required parameters structure
   - Type versions available

2. **Context7 provides:**
   - Current n8n HTTP Request documentation
   - Latest authentication patterns
   - Up-to-date error handling syntax
   - Current retry configuration options

3. **Result:**
   - Working node with correct typeVersion
   - No deprecated authentication methods
   - Current error handling patterns

---

### Example 2: Using Latest n8n Webhook Features

**Prompt:**
```
Create a webhook trigger node with:
- Custom response code (201 Created)
- Response headers for CORS
- JSON body validation
- Path parameter extraction

Use the latest n8n webhook capabilities. use context7
```

**What Context7 Adds:**
- Documentation for n8n v1.73+ webhook features (if latest)
- Current responseMode options
- Latest CORS header syntax
- Path parameter patterns introduced in recent versions

**Without Context7:**
- Might use deprecated responseMode values
- Could miss new path parameter features
- Might suggest outdated CORS patterns

---

### Example 3: Complex Multi-Node Workflow with Current Best Practices

**Prompt:**
```
Build a complete BCP (Buyer Card Profile) data processing workflow:

Phase 1: Data Intake
- Webhook receives supplier data
- Validate required fields
- Enrich with Perplexity API search

Phase 2: Processing
- Transform data to BCP format
- Query Neo4j for existing relationships
- Calculate risk scores

Phase 3: Storage & Notification
- Store in PostgreSQL
- Update Neo4j graph
- Send Slack notification

Requirements:
- Use latest n8n node versions
- Implement current error handling patterns
- Follow 2025 best practices for credentials

Follow N8N_WORKFLOW_CREATION_PROMPT.md 5-phase process. use context7
```

**What Context7 Provides:**

1. **Latest n8n Best Practices (2025):**
   - Current credential management patterns
   - Up-to-date error node configurations
   - Latest workflow variable syntax

2. **Current Node Documentation:**
   - PostgreSQL node latest features
   - Neo4j node current query patterns
   - Slack node newest notification options

3. **Version-Specific Features:**
   - Features available in your n8n version
   - Deprecated parameters to avoid
   - New parameters introduced recently

**Result:** Production-ready workflow using current APIs and patterns, not outdated 2023 examples.

---

## 🎯 When to Use Context7 with n8n-mcp

### ✅ ALWAYS Use Context7 When:

1. **Working with external APIs in n8n nodes**
   - HTTP Request nodes connecting to third-party services
   - API nodes that might have changed (Slack, Google Sheets, etc.)

2. **Using newly released n8n features**
   - Features added in last 6 months
   - Nodes you haven't used before
   - Beta or experimental capabilities

3. **Building production workflows**
   - Need current security patterns
   - Require latest credential management
   - Must follow current best practices

4. **Troubleshooting "red dot" errors**
   - Parameters might be deprecated
   - New required fields might exist
   - Authentication patterns might have changed

### ⚠️ Optional (Context7 Adds Less Value) When:

1. **Using stable, core nodes that rarely change**
   - Manual Trigger
   - Set node
   - IF node
   - Switch node

2. **Working on simple workflows**
   - 2-3 node workflows
   - No external API calls
   - Standard internal operations

3. **Following existing templates exactly**
   - Copying proven workflow patterns
   - Using well-tested examples from your repository

---

## 🔧 Integration with Existing n8n Documentation Suite

### Updated Workflow Creation Sequence

**Before (n8n-mcp only):**

```
Phase 0: Template Search
  ↓ list-workflows, get-workflow
Phase 1: Node Discovery
  ↓ search_nodes, list_nodes
Phase 2: Essential Properties
  ↓ get_node_essentials
Phase 3: Documentation Review
  ↓ tools_documentation
Phase 4: Workflow Construction
Phase 5: Validation
```

**After (n8n-mcp + Context7):**

```
Phase 0: Template Search
  ↓ list-workflows, get-workflow
Phase 1: Node Discovery
  ↓ search_nodes, list_nodes
Phase 2: Essential Properties
  ↓ get_node_essentials
Phase 3: Documentation Review
  ↓ tools_documentation (n8n-mcp)
  ↓ use context7 (current n8n docs) ← NEW
Phase 4: Workflow Construction
  ↓ use context7 (validate APIs) ← NEW
Phase 5: Validation
```

**Changes:**
- Phase 3: Add Context7 for current n8n documentation
- Phase 4: Use Context7 during construction for API validation

---

## 📋 Enhanced Workflow Creation Prompt Template

Copy this template when creating n8n workflows with Context7:

```markdown
## Project: [Workflow Name]

### Objective
[Describe what the workflow should do]

### Requirements
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]

### Technical Constraints
- n8n version: [Your version, e.g., v1.73+]
- External APIs: [List APIs you'll integrate]
- Data sources: [PostgreSQL, Neo4j, etc.]

### Instructions

Follow the 5-phase validation process from N8N_WORKFLOW_CREATION_PROMPT.md:

**Phase 0: Template Search**
- Query n8n-mcp for existing templates matching this use case
- Tools: `list-workflows`, `get-workflow`

**Phase 1: Node Discovery**
- Search for required node types
- Tools: `search_nodes`, `list_nodes`

**Phase 2: Essential Properties**
- Get current schemas for selected nodes
- Tools: `get_node_essentials`

**Phase 3: Documentation Review**
- Review n8n-mcp tool documentation
- **NEW:** Fetch current n8n documentation with `use context7`

**Phase 4: Workflow Construction**
- Build complete workflow JSON
- **NEW:** Validate all external API calls with `use context7`

**Phase 5: Pre-Deployment Validation**
- Run AI Workflow Validation checklist
- Verify no deprecated parameters (Context7 will catch these)

### Additional Context
[Any specific requirements, constraints, or preferences]

**use context7**
```

---

## 🎓 Best Practices

### 1. Optimize Context7 Queries

**❌ DON'T: Vague requests**
```
Build an n8n workflow. use context7
```

**✅ DO: Specific context requests**
```
Build an n8n HTTP Request node with OAuth2 authentication
using the latest n8n credential system. use context7
```

---

### 2. Layer Your Information Sources

**Information Hierarchy:**

1. **n8n-mcp** → Structure (what nodes exist, required parameters)
2. **Context7** → Content (current documentation, latest APIs)
3. **Your templates** → Patterns (proven workflows in your environment)

**Example Prompt:**
```
Using n8n-mcp, list available PostgreSQL nodes.

Then, using Context7, get the latest documentation for the
PostgreSQL node to understand current connection patterns.

Finally, build a node configuration that matches the pattern
used in workflow "BCP_Data_Pipeline_v6" from my templates.

use context7
```

---

### 3. Cache Context7 Results (Implicit)

Context7 caches documentation automatically. For repetitive workflow creation:

**First Request:**
```
Create Slack notification node with current API. use context7
```
*Context7 fetches Slack node docs*

**Second Request (same session):**
```
Add another Slack node for error notifications
```
*Context7 reuses cached Slack documentation*

**Benefit:** Faster responses, lower API usage

---

### 4. Version-Specific Requests

If you know your n8n version, specify it:

**Example:**
```
Create an IF node using n8n v1.73 conditional logic syntax.
Ensure compatibility with this version. use context7
```

---

### 5. Combine with N8N_NODE_VALIDATION_PROTOCOL.md

**Reference the validation checklist:**

```
Create a webhook → HTTP → Slack workflow.

Follow these validations:
1. ✅ Node Type Exists (check with n8n-mcp search_nodes)
2. ✅ Required Parameters Present (get_node_essentials)
3. ✅ Type Version Correct (validate with Context7 current docs)
4. ✅ Credentials Configured (use Context7 for latest patterns)
5. ✅ Connections Valid (verify with n8n-mcp)

use context7
```

---

## 🔍 Troubleshooting

### Issue 1: Context7 Not Activating

**Symptoms:**
- Prompt includes "use context7" but no documentation injected
- AI uses outdated examples

**Solutions:**

1. **Check MCP connection:**
   - Open Cursor → Settings → MCP Servers
   - Verify Context7 shows green indicator
   - If red, restart Cursor

2. **Verify configuration:**
```json
{
  "Context7": {
    "url": "https://mcp.context7.com/mcp",  // Must be exact
    "headers": {}  // or {"CONTEXT7_API_KEY": "..."}
  }
}
```

3. **Check prompt placement:**
   - `use context7` must be in the SAME message as your request
   - Place at end of prompt for best results

---

### Issue 2: Context7 Returns Generic Results

**Symptoms:**
- Documentation is too general
- Not specific to your n8n use case

**Solutions:**

**❌ Too Generic:**
```
Build a workflow. use context7
```

**✅ Specific Request:**
```
Create an n8n HTTP Request node that posts JSON data to a REST API
with Bearer token authentication. Include error handling for 401/429
responses. Use the latest n8n authentication patterns. use context7
```

---

### Issue 3: Conflicting Information (n8n-mcp vs. Context7)

**Symptoms:**
- n8n-mcp shows one parameter structure
- Context7 documentation suggests different structure

**Resolution Priority:**

1. **n8n-mcp wins for structure** (it reflects your actual n8n instance)
2. **Context7 wins for content** (it has latest documentation)
3. **Your instance wins overall** (if something works in your n8n, that's truth)

**Example:**
```
n8n-mcp says: "authentication" parameter required
Context7 docs say: Use "auth" parameter (deprecated syntax from old docs)

✅ CORRECT: Use "authentication" (n8n-mcp reflects actual schema)
```

---

### Issue 4: Rate Limiting

**Symptoms:**
- Context7 requests slow down
- Timeout errors

**Solutions:**

1. **Get API key** from https://context7.com/dashboard
2. **Add to configuration:**
```json
{
  "Context7": {
    "url": "https://mcp.context7.com/mcp",
    "headers": {
      "CONTEXT7_API_KEY": "your-api-key"
    }
  }
}
```

3. **Cache requests** - Reuse documentation from recent queries in same session

---

## 📊 Context7 + n8n-mcp Use Cases

### Use Case 1: Updating Legacy Workflows

**Scenario:** You have a 2023 n8n workflow that needs modernization

**Prompt:**
```
I have an existing n8n workflow from 2023 with these nodes:
- Webhook Trigger
- HTTP Request (typeVersion 2)
- Google Sheets (typeVersion 1)
- Slack notification

Update this workflow to use:
- Latest node type versions
- Current authentication patterns
- Modern error handling

use context7
```

**What Context7 Provides:**
- Current typeVersions for each node
- Deprecated parameters to remove
- New parameters to add
- Updated authentication methods

---

### Use Case 2: Integrating New Third-Party APIs

**Scenario:** Add a new API integration to n8n

**Prompt:**
```
Create an n8n HTTP Request node to integrate with Perplexity AI API:
- Endpoint: https://api.perplexity.ai/chat/completions
- Method: POST
- Authentication: Bearer token in headers
- Body: JSON with model and messages parameters

Ensure the configuration matches Perplexity's current API spec (2025).

use context7
```

**What Context7 Provides:**
- Current Perplexity API documentation
- Exact request format
- Required headers
- Error response patterns

**What n8n-mcp Provides:**
- HTTP Request node schema
- How to structure the node in n8n
- Parameter placement in workflow JSON

---

### Use Case 3: Complex Multi-Step Automation

**Scenario:** Build sophisticated BCP data pipeline

**Prompt:**
```
Build a complete BCP intelligence pipeline:

1. Webhook receives supplier data
2. Perplexity API enriches data
3. PostgreSQL stores enriched data
4. Neo4j creates knowledge graph relationships
5. Slack sends notification
6. Error handler catches all failures

Requirements:
- Use latest n8n credential system
- Implement current retry patterns
- Follow 2025 security best practices
- All external APIs must use current specs

Reference: N8N_WORKFLOW_CREATION_PROMPT.md 5-phase process

use context7
```

**How Both Servers Work Together:**

| Phase | n8n-mcp | Context7 |
|-------|---------|----------|
| Template Search | Lists existing BCP workflows | - |
| Node Discovery | Shows available nodes for PostgreSQL, Neo4j, Slack | - |
| Essential Properties | Provides node schemas | Provides current API docs for external services |
| Documentation | n8n node documentation | Current Perplexity/PostgreSQL/Neo4j/Slack API docs |
| Construction | Workflow JSON structure | API request formats, auth patterns |
| Validation | Checks n8n workflow validity | Validates external API calls |

---

## 🎯 Quick Reference Card

### When to Use What

| Task | Tool | Example |
|------|------|---------|
| Find if node exists | n8n-mcp | `search_nodes("HTTP")` |
| Get node schema | n8n-mcp | `get_node_essentials` |
| Get current n8n docs | Context7 | `use context7` |
| Get external API docs | Context7 | `use context7` |
| List templates | n8n-mcp | `list-workflows` |
| Create workflow | n8n-mcp | `create-workflow` |
| Validate workflow | n8n-mcp | AI Workflow Validation |
| Check API changes | Context7 | `use context7` |

---

### Context7 Prompt Patterns

| Pattern | When to Use | Example |
|---------|-------------|---------|
| `use context7` (end of prompt) | General documentation | "Create webhook node. use context7" |
| `Use latest [library] API. use context7` | Specific library focus | "Use latest Slack API. use context7" |
| `Following 2025 best practices. use context7` | Modern patterns | "Following 2025 best practices. use context7" |
| `Version-specific: [version]. use context7` | Targeting specific version | "Version-specific: n8n v1.73. use context7" |

---

## 🔗 Integration with Document Suite

This guide is part of the **n8n MCP Documentation Suite**:

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [N8N_QUICK_START.md](N8N_QUICK_START.md) | 5-minute quick start | First-time setup |
| [N8N_WORKFLOW_CREATION_PROMPT.md](N8N_WORKFLOW_CREATION_PROMPT.md) | AI prompt template | Creating any workflow |
| [N8N_NODE_VALIDATION_PROTOCOL.md](N8N_NODE_VALIDATION_PROTOCOL.md) | Complete reference | Deep technical validation |
| **[CONTEXT7_N8N_INTEGRATION_GUIDE.md](CONTEXT7_N8N_INTEGRATION_GUIDE.md)** | Context7 integration | Current docs + API validation ← **YOU ARE HERE** |

---

## 📞 Support & Resources

### Context7 Resources
- **Dashboard:** https://context7.com/dashboard
- **GitHub:** https://github.com/upstash/context7
- **Documentation:** https://upstash.com/docs/context7

### n8n MCP Resources
- **n8n-mcp GitHub:** https://github.com/n8n-io/n8n-mcp
- **n8n Documentation:** https://docs.n8n.io
- **Community Forum:** https://community.n8n.io

### Combined Support
- Ask in n8n Community with `[mcp]` tag
- Report Context7 issues: https://github.com/upstash/context7/issues
- Report n8n-mcp issues: https://github.com/n8n-io/n8n-mcp/issues

---

## ✅ Summary

**Context7 MCP provides:**
- ✅ Up-to-date documentation for n8n and external APIs
- ✅ Elimination of API hallucinations
- ✅ Version-specific code examples
- ✅ Current best practices (2025)

**When combined with n8n-mcp:**
- ✅ Complete workflow structure validation (n8n-mcp)
- ✅ Current API documentation (Context7)
- ✅ No deprecated code patterns
- ✅ Production-ready, modern workflows

**Usage pattern:**
```
[Your workflow requirements]

Follow N8N_WORKFLOW_CREATION_PROMPT.md 5-phase process

use context7
```

**Current setup status:**
- ✅ Context7 configured in your mcp.json
- ✅ n8n-mcp configured with API key
- ✅ Ready to use both together

**Recommended next step:**
Get Context7 API key from https://context7.com/dashboard for higher rate limits

---

**Version:** 1.0
**Last Updated:** 2025-11-09
**Author:** Claude Code (Sonnet 4.5)
**Status:** Production Ready
