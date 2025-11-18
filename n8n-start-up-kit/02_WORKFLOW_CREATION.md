---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-N8N-002"
component_name: "n8n Workflow Creation Guide"
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
integrates_with: ["INT-RSN-001", "INT-N8N-003"]
api_endpoints: []
data_sources: ["n8n-mcp", "context7-mcp"]
outputs: ["n8n_workflows"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: false
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "AI prompt template for creating production-ready n8n workflows with zero errors"
summary: "5-phase workflow creation process with MCP validation, Context7 integration, and comprehensive verification"
business_value: "Enables rapid n8n workflow development with validated configurations and current API specifications"
success_metrics: ["workflow_creation_time < 10min", "error_rate = 0", "first_deploy_success >= 0.95"]

# === TAGS & CLASSIFICATION ===
tags: ["n8n", "workflow", "automation", "mcp", "context7", "prompt-template"]
keywords: ["n8n", "workflow", "mcp", "automation", "validation", "context7", "5-phase"]
related_components: ["INT-N8N-001", "INT-N8N-003", "INT-RSN-001"]
startup_required: false
mode_type: "documentation"
---

# 🤖 Perfect n8n Workflow Creation Prompt

**Purpose:** Generate production-ready n8n workflows with zero errors, correct configurations, and no deprecated nodes.

**Version:** 2.0 | **Last Updated:** 2025-01-27 | **Compatible with:** n8n-mcp v2.17.0+

---

## 📚 Document Suite Overview

This is part of the **n8n MCP Documentation Suite**:

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[04_VALIDATION_PROTOCOL.md](04_VALIDATION_PROTOCOL.md)** | Complete reference guide | When you need detailed information about MCP servers, tools, and validation |
| **[02_WORKFLOW_CREATION.md](02_WORKFLOW_CREATION.md)** | AI prompt template ← **YOU ARE HERE** | When asking AI to create n8n workflows (copy-paste prompt) |
| **[03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md)** | Context7 + n8n integration | When you need up-to-date n8n/API documentation |
| **[06_QUICK_START.md](06_QUICK_START.md)** | 5-minute quick start | When you want a working example immediately |

**Recommended Reading Order:**
1. **New users:** Start with Quick Start → Protocol (skim) → Workflow Prompt
2. **AI assistants:** Use Workflow Prompt → Reference Protocol as needed → Add Context7 for current docs
3. **Developers:** Read Gap Analysis → Protocol → Context7 Integration → Implement with Prompt

---

## 🎯 OBJECTIVE

Create a fully functional n8n workflow with:
- ✅ All fields correctly configured
- ✅ No broken nodes
- ✅ No deprecated nodes
- ✅ No broken connections
- ✅ Proper credentials setup
- ✅ Error handling
- ✅ Pre-validated configuration

---

## 🔍 MCP Terminology: Resources vs. Tools

**IMPORTANT DISTINCTION:** The Model Context Protocol defines two types of capabilities:

### MCP Resources (Read-Only Data)
- **What they are:** Queryable data sources (like database tables or API endpoints)
- **How to use:** Query with parameters, receive data
- **Examples in n8n-mcp:**
  - `search_nodes` - Query node database
  - `get_node_essentials` - Retrieve node properties
  - `tools_documentation` - Fetch documentation

**Usage Pattern:**
```python
# Query a resource
result = mcp_client.read_resource("search_nodes", {"query": "HTTP"})
```

### MCP Tools (Executable Functions)
- **What they are:** Functions that perform actions (like API methods)
- **How to use:** Call with parameters, trigger action
- **Examples in n8n Instance MCP:**
  - `create-workflow` - Creates new workflow
  - `activate-workflow` - Activates existing workflow
  - `delete-execution` - Removes execution record

**Usage Pattern:**
```python
# Call a tool
result = mcp_client.call_tool("create-workflow", {"name": "My Workflow", "nodes": [...]})
```

**In This Documentation:**
- When we say "Query MCP Resource" → Use for node documentation (Server A)
- When we say "Call MCP Tool" → Use for workflow management (Server B)

---

## 📋 OPTIMAL TOOL USAGE SEQUENCE

### Phase 0: Template Search (ALWAYS START HERE)
**Goal:** Find existing patterns to build upon

**MCP Resources to Query:**
1. **`list_nodes`** - Browse available templates by category
2. **Workflow Templates** - Access 2,646 pre-built configurations

**What to Ask:**
```
"Search for existing n8n workflow templates that are similar to: [YOUR WORKFLOW DESCRIPTION]"
```

**Expected Output:**
- List of similar workflow templates
- Template IDs and descriptions
- Reusable patterns

---

### Phase 1: Node Discovery & Validation
**Goal:** Identify exact nodes needed and their current specifications

**MCP Resources to Query:**
1. **`search_nodes`** - Find nodes by functionality
2. **`list_nodes`** - Browse nodes by category (if needed)

**What to Ask:**
```
"What are the exact, current node names for:
- [Node Type 1: e.g., HTTP Request]
- [Node Type 2: e.g., Slack notification]
- [Node Type 3: e.g., Data transformation]

Return the full node type identifiers (e.g., 'n8n-nodes-base.httpRequest')"
```

**Expected Output:**
- Exact node type identifiers
- Node version numbers
- Availability confirmation

---

### Phase 2: Essential Properties Extraction
**Goal:** Get ONLY the required and essential optional properties

**MCP Resources to Query:**
1. **`get_node_essentials`** - Get 10-20 key properties per node

**What to Ask:**
```
"For each node:
- [Node Type 1: n8n-nodes-base.httpRequest]
- [Node Type 2: n8n-nodes-base.slack]

Provide:
1. REQUIRED properties with data types
2. Essential OPTIONAL properties with defaults
3. Valid enum values for select fields
4. Current property names (not deprecated)"
```

**Expected Output:**
- Required properties list
- Property data types and constraints
- Valid enum values
- Default values

---

### Phase 3: Documentation Review
**Goal:** Understand node behavior and best practices with CURRENT documentation from multiple authoritative sources

**MCP Resources to Query (Priority Order):**
1. **Official n8n Docs** - Scrape docs.n8n.io for authoritative examples and best practices (via Firecrawl MCP) ← **HIGHEST PRIORITY**
2. **`tools_documentation`** - Get detailed node documentation (from n8n-mcp)
3. **Context7 MCP** - Get up-to-date n8n documentation from source repositories ← **Secondary reference**

**What to Ask:**
```
"Provide documentation for these nodes:
- [Node Type 1]
- [Node Type 2]

Include:
- Usage examples
- Common configurations
- Best practices
- Known limitations
- Authentication requirements

Sources to check (in priority order):
1. Official n8n docs website: https://docs.n8n.io/integrations/builtin/nodes/[node-name]/ ← **CHECK FIRST (HIGHEST PRIORITY)**
2. n8n-mcp tools_documentation (node schemas)
3. Context7 (current source repo docs) ← **Secondary reference**

use context7"
```

**Expected Output:**
- Node usage examples (from n8n-mcp)
- Current n8n documentation (from Context7)
- Official docs examples and best practices (from docs.n8n.io)
- Configuration patterns
- Authentication details
- Latest API specifications

**Why Check Official Docs Website?**
- **Authoritative source:** Official n8n documentation is the definitive reference
- **Complete examples:** Often includes real-world use cases not in source repos
- **Best practices:** Official docs highlight recommended patterns and anti-patterns
- **Version-specific guides:** May have version-specific migration guides
- **Community examples:** Links to community workflows and templates

**Why Use Multiple Sources?**
- **n8n-mcp:** Validates against YOUR actual instance (what nodes/types exist)
- **Official docs:** Gets curated examples and best practices (what n8n recommends) ← **HIGHEST PRIORITY**
- **Context7:** Gets current source code documentation (what's in the repo) ← **Secondary reference**

**How to Access Official Docs:**
```
"Scrape the official n8n documentation for [node name] from:
https://docs.n8n.io/integrations/builtin/nodes/[node-name]/

Focus on:
- Usage examples
- Configuration best practices
- Common use cases
- Known limitations"
```

**Learn More:** See [03_CONTEXT7_REFERENCE.md](03_CONTEXT7_REFERENCE.md) for complete Context7 usage patterns

---

### Phase 4: Workflow Construction
**Goal:** Build complete workflow JSON with validated configurations and current APIs

**What to Request:**
```
"Build a complete n8n workflow JSON with:
- All nodes from Phase 1 configured with properties from Phase 2
- All connections properly defined
- Credentials placeholders (don't include actual secrets)
- Proper node positioning for readability

Validate all external API calls use current specifications.

use context7"
```

**Why Use Context7 Here?**
- Validates external API endpoints are current
- Ensures authentication patterns match latest API specs
- Catches API version changes (e.g., Slack API v2 deprecation)
- Prevents using outdated request formats

**Original Request (Without Context7):**
```
"Create a complete n8n workflow JSON that:

1. Uses ONLY the validated node types from Phase 1
2. Configures ONLY the properties from Phase 2
3. Follows patterns from Phase 3 documentation
4. Includes these components:
   - All nodes with proper IDs and positions
   - All connections between nodes
   - Credential references (not values)
   - Error handling nodes (if applicable)
   - Proper typeVersion for each node

5. Ensures:
   - No deprecated properties
   - All required fields populated
   - Valid connection indices
   - No circular dependencies
   - Minimum 2 nodes (unless single webhook)

Output complete workflow JSON ready for import."
```

---

### Phase 5: Pre-Deployment Validation
**Goal:** Validate workflow before deployment

**MCP Resources to Query:**
1. **AI Workflow Validation** - Comprehensive validation check

**What to Ask:**
```
"Validate this workflow configuration:
[PASTE WORKFLOW JSON]

Check for:
1. Missing required properties
2. Invalid property values
3. Broken connections
4. Missing nodes in connection references
5. Circular dependencies
6. Deprecated node types or properties
7. Invalid credential references
8. AI agent workflow compliance (if applicable)

Provide detailed error report with line numbers and fixes."
```

**Expected Output:**
- Validation results
- Error list with specific fixes
- Warnings about best practices

---

## 🚀 COMPLETE WORKFLOW CREATION PROMPT

**Copy and paste this prompt when asking Cursor to create an n8n workflow:**

```markdown
# Create n8n Workflow: [YOUR WORKFLOW DESCRIPTION]

Follow this exact sequence using n8n-mcp resources:

## Phase 0: Template Search
Search for existing n8n workflow templates similar to: [DESCRIPTION]
- Query MCP resource: workflow templates
- Goal: Find reusable patterns

## Phase 1: Node Discovery
Identify exact, current node types needed for:
1. [Functionality 1: e.g., "trigger on webhook POST"]
2. [Functionality 2: e.g., "fetch data from HTTP API"]
3. [Functionality 3: e.g., "send Slack notification"]

**Query MCP resource:** `search_nodes` and `list_nodes`
**Return:** Full node type identifiers (e.g., "n8n-nodes-base.webhook")

## Phase 2: Essential Properties
For each identified node, get essential properties:
- REQUIRED properties with types
- Essential OPTIONAL properties with defaults
- Valid enum values for select fields
- Current (non-deprecated) property names

**Query MCP resource:** `get_node_essentials`

## Phase 3: Documentation Review
Retrieve detailed documentation for each node from multiple sources:
- Usage examples
- Best practices
- Authentication requirements
- Common configurations

**Query MCP resources (Priority Order):**
1. **Official n8n docs (docs.n8n.io)** - Authoritative examples and best practices ← **CHECK FIRST (HIGHEST PRIORITY)**
2. `tools_documentation` (n8n-mcp) - Node schemas from your instance
3. Context7 - Current source repository documentation ← **Secondary reference**

**For official docs, scrape:**
```
https://docs.n8n.io/integrations/builtin/nodes/[node-name]/
```

## Phase 4: Build Workflow
Create complete workflow JSON including:

### Required Components:
- **Nodes array** with:
  - Unique IDs for each node
  - Proper node types from Phase 1
  - Complete parameters from Phase 2
  - Position coordinates [x, y]
  - Type version numbers
  - Credential references (structure only, no values)

- **Connections object** with:
  - Valid source → target mappings
  - Correct connection types (main, error)
  - Proper array indices
  - No broken references

- **Workflow metadata**:
  - Workflow name
  - Active: false (for testing)
  - Settings: {}
  - Tags: []

### Validation Requirements:
✅ All required properties populated
✅ No deprecated nodes or properties
✅ All connection targets exist in nodes array
✅ No circular dependencies
✅ Credentials referenced but not embedded
✅ Error handling included (if needed)
✅ At least 2 nodes (unless single webhook trigger)

## Phase 5: Validate
Before showing me the final workflow:
1. Query MCP resource: AI Workflow Validation
2. Check for all common errors
3. Fix any issues found
4. Re-validate until clean

## Final Output
Provide:
1. ✅ Complete, validated workflow JSON
2. 📋 List of credentials needed (with types, not values)
3. 📝 Setup instructions
4. ⚠️ Any warnings or optional improvements
5. 🔗 Connection diagram (text format)

---

## Workflow Requirements:
[DESCRIBE YOUR WORKFLOW HERE - BE SPECIFIC]

Example:
- Trigger: Webhook on POST to /data-intake
- Action 1: Validate incoming JSON schema
- Action 2: HTTP Request to external API
- Action 3: Transform data using Code node
- Action 4: Send result to Slack channel
- Error Handling: Catch all errors and log to file

---

## Additional Context:
- n8n Version: [if known]
- Existing Credentials: [list credential names if they exist]
- Integration Requirements: [specific API versions, etc.]
- Performance Needs: [batch size, frequency, etc.]

---

## Success Criteria:
✅ Workflow imports without errors
✅ All nodes are current (not deprecated)
✅ All connections are valid
✅ All required fields are populated
✅ Credentials are properly referenced
✅ Error handling is implemented
✅ Workflow is ready for testing
```

---

## 📊 VERIFICATION CHECKLIST

After Cursor generates the workflow, verify:

### Workflow Structure
- [ ] `name` field is present and descriptive
- [ ] `nodes` array contains at least 2 nodes (unless single webhook)
- [ ] `connections` object properly links all nodes
- [ ] `active` is set to `false` for initial testing
- [ ] `settings` and `tags` objects are present

### Node Validation
- [ ] All nodes have unique `id` fields
- [ ] All nodes have valid `type` (format: "n8n-nodes-base.nodeName")
- [ ] All nodes have `typeVersion` specified
- [ ] All nodes have `position` coordinates [x, y]
- [ ] All nodes have `parameters` object (even if empty)

### Property Validation
- [ ] All REQUIRED properties are populated
- [ ] No deprecated property names
- [ ] Enum values are valid (from Phase 2)
- [ ] Data types match specifications
- [ ] Expressions use proper n8n syntax (={{ ... }})

### Connection Validation
- [ ] All connection sources exist in nodes array
- [ ] All connection targets exist in nodes array
- [ ] Connection types are valid (main, error, etc.)
- [ ] Array indices are correct
- [ ] No circular references

### Credential Validation
- [ ] Credentials are referenced, not embedded
- [ ] Credential type matches node requirements
- [ ] Credential structure follows format:
  ```json
  "credentials": {
    "credentialType": {
      "id": "credential-id",
      "name": "Credential Name"
    }
  }
  ```

### Error Handling
- [ ] Error outputs are connected (if applicable)
- [ ] Try/catch patterns implemented (if needed)
- [ ] Fallback nodes configured (if needed)

---

## 🎓 BEST PRACTICES

### 1. Always Start with Templates
Before building from scratch, search the 2,646 templates. This:
- Saves 80-90% development time
- Ensures best practices
- Reduces validation errors
- Provides proven patterns

### 2. Use get_node_essentials, Not Full Schema
Request only essential properties (10-20) instead of full schemas (200+):
- Faster queries
- Clearer requirements
- Less chance of using deprecated fields
- Better token efficiency

### 3. Validate Early and Often
- After Phase 1: Confirm node types exist
- After Phase 2: Verify property names are current
- After Phase 4: Run full AI workflow validation
- Before deployment: Final check

### 4. Document Credentials Separately
Never embed credential values in workflow JSON:
- Reference by ID and name only
- Document required credential types
- Provide setup instructions separately

### 5. Include Error Handling
For production workflows:
- Add error output connections
- Include fallback nodes
- Log errors appropriately
- Set up notifications for failures

---

## ⚠️ COMMON PITFALLS TO AVOID

### ❌ DON'T:
1. **Use node names without validation**
   - Wrong: Assume "HTTP" node exists
   - Right: Query `search_nodes` for exact name

2. **Skip template search**
   - Wrong: Build from scratch immediately
   - Right: Search 2,646 templates first

3. **Use all properties from full schema**
   - Wrong: Configure 200+ properties
   - Right: Use `get_node_essentials` for 10-20 key properties

4. **Embed credentials in JSON**
   - Wrong: `"password": "secret123"`
   - Right: Reference credential ID only

5. **Skip validation**
   - Wrong: Generate and deploy immediately
   - Right: Validate with AI Workflow Validation first

6. **Ignore deprecated warnings**
   - Wrong: Use old property names
   - Right: Check documentation for current names

---

## 🔧 TROUBLESHOOTING

### "Node type not found"
**Cause:** Using incorrect node type identifier
**Fix:** Query `search_nodes` for exact type name

### "Required property missing"
**Cause:** Didn't consult `get_node_essentials`
**Fix:** Query essential properties and populate all required fields

### "Connection target not found"
**Cause:** Node name mismatch in connections object
**Fix:** Ensure connection targets match exact node names in nodes array

### "Deprecated property"
**Cause:** Using outdated documentation
**Fix:** Use `tools_documentation` to get current property names

### "Credential type mismatch"
**Cause:** Wrong credential type for node
**Fix:** Check node documentation for required credential type

---

## 🔑 How to Get Your n8n API Key

### For n8n Cloud Users:

1. **Login to your n8n instance:** https://[your-instance].app.n8n.cloud
2. **Navigate to Settings:**
   - Click your profile icon (top-right)
   - Select "Settings"
3. **Go to API section:**
   - Click "API" in left sidebar
4. **Generate new key:**
   - Click "Create API Key"
   - Give it a descriptive name (e.g., "MCP Server Access")
   - Copy the key immediately (shown only once!)
5. **Set permissions:**
   - Ensure key has "workflows:read", "workflows:write", "credentials:read"

### For Self-Hosted Users:

1. **Access admin panel:** http://localhost:5678 (or your custom URL)
2. **Navigate to credentials:**
   - Go to "Settings" → "API"
3. **Create new API key:**
   - Click "Create Key"
   - Name: "n8n-mcp-server"
   - Permissions: Full access (or minimal: workflows, executions, credentials)
4. **Save securely:**
   ```bash
   echo "export N8N_API_KEY='n8n_api_...'" >> ~/.bashrc
   source ~/.bashrc
   ```

### Test Your API Key:

```bash
# Test connection
curl -H "X-N8N-API-KEY: $N8N_API_KEY" \
     "$N8N_URL/api/v1/workflows" | jq '.data | length'

# Should return: number of workflows (e.g., 5)
```

### Troubleshooting:
- **401 Unauthorized:** Key is invalid or expired
- **403 Forbidden:** Key lacks required permissions
- **404 Not Found:** N8N_URL is incorrect

---

## 🚀 How to Deploy Your Workflow to n8n

### Step 1: Save the Workflow JSON

After AI generates your workflow, save it to a file:
```bash
# Copy the JSON output
# Save as: my-workflow.json
```

### Step 2: Import to n8n UI

1. **Login to your n8n instance**
   - Cloud: https://[your-instance].app.n8n.cloud
   - Self-hosted: http://localhost:5678

2. **Create new workflow**
   - Click "+ Add workflow" (top-right corner)

3. **Import the JSON**
   - Click the "⋮" menu (three dots, top-right)
   - Select "Import from File"
   - Choose your `my-workflow.json` file
   - Click "Open"

4. **Verify import successful**
   - ✅ All nodes appear on canvas
   - ✅ Connections are drawn between nodes
   - ✅ No red error indicators

### Step 3: Configure Credentials

For each node requiring authentication:

1. **Click the node** with credential requirement
2. **In right panel, find "Credentials" section**
3. **Click "Create New" or select existing**
4. **Fill in required fields:**
   - API keys
   - OAuth tokens
   - Database connections
   - etc.
5. **Click "Save"**
6. **Test credential** (click "Test" button if available)

### Step 4: Test the Workflow

1. **Test individual nodes:**
   - Click a node
   - Click "Execute Node" button
   - Verify output in right panel

2. **Test complete workflow:**
   - Click "Test workflow" button (top)
   - Check execution results
   - Verify all nodes completed successfully

3. **Fix any errors:**
   - Red indicators show errors
   - Click node to see error details
   - Fix configuration
   - Re-test

### Step 5: Activate the Workflow

1. **Review execution mode:**
   - Manual trigger: No activation needed
   - Webhook/Schedule: Must activate

2. **Activate:**
   - Toggle "Active" switch (top-right)
   - Should turn green

3. **Monitor executions:**
   - Go to "Executions" tab
   - See real-time workflow runs
   - Debug any failures

### Common Import Errors:

**"Invalid workflow JSON"**
- Fix: Validate JSON syntax (use jsonlint.com)
- Ensure complete JSON (no truncation)

**"Node type not found"**
- Fix: Install required community nodes
- Or use core node alternatives

**"Credential type mismatch"**
- Fix: Check credential type in node
- Create correct credential type

**"Connection references missing node"**
- Fix: Ensure all node names in connections exist in nodes array
- Check for typos in node names

---

## 📚 ADDITIONAL RESOURCES

- **n8n-mcp Documentation:** https://github.com/czlonkowski/n8n-mcp
- **n8n Workflow Templates:** 2,646 available via MCP resource query
- **Node Documentation:** Query via `tools_documentation` resource
- **n8n Official Docs:** https://docs.n8n.io
- **n8n Community Forum:** https://community.n8n.io
- **n8n Discord:** https://discord.gg/n8n

---

**Last Updated:** 2025-11-09
**Version:** 2.0
**Maintained by:** Igor Beylin
**Compatible with:** n8n-mcp v2.17.0+, n8n Cloud/Self-hosted v1.0+
