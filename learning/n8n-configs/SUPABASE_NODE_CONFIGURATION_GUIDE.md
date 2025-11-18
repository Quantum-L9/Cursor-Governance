---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "LRN-008"
component_name: "Supabase Node Configuration Guide"
layer: "intelligence"
domain: "learning"
type: "learning"
status: "active"
created: "2025-10-13T00:00:00Z"
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
integrates_with: ["LRN-001", "LRN-002", "LRN-004", "SEC-003"]
api_endpoints: []
data_sources: ["n8n_supabase_configs", "workflow_patterns"]
outputs: ["configuration_guides", "fix_scripts", "validation_checklists"]

# === OPERATIONAL METADATA ===
execution_mode: "reference"
monitoring_required: false
logging_level: "info"
performance_tier: "reference"

# === BUSINESS METADATA ===
purpose: "Complete guide for configuring Supabase nodes in n8n workflows with proper credentials and environment variables"
summary: "Comprehensive learning guide providing complete Supabase node configuration standards, credential setup, automated fix scripts, manual configuration steps, validation, and troubleshooting"
business_value: "Ensures consistent Supabase node configuration reducing setup time and preventing configuration errors"
success_metrics: ["configuration_consistency >= 0.95", "setup_time_reduction >= 0.80", "error_prevention_rate >= 0.90"]

# === INTEGRATION METADATA ===
suite_2_origin: "SUPABASE_NODE_CONFIGURATION_GUIDE.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive Supabase configuration guide"

# === TAGS & CLASSIFICATION ===
tags: ["learning", "n8n", "supabase", "configuration", "guide"]
keywords: ["supabase", "n8n", "configuration", "guide", "credentials", "environment-variables"]
related_components: ["LRN-001", "LRN-002", "LRN-004", "SEC-003"]
startup_required: false
mode_type: "learning"
---

# Supabase Node Configuration Guide for n8n Workflows

**Purpose:** Complete guide for configuring Supabase nodes in n8n workflows with proper credentials and environment variables.

**Use this guide when:** Setting up new agents, fixing existing workflows, or standardizing Supabase usage across your automation ecosystem.

---

## 📋 Table of Contents

1. [Understanding the Architecture](#understanding-the-architecture)
2. [Supabase Node Configuration Standard](#supabase-node-configuration-standard)
3. [Environment Variables Setup](#environment-variables-setup)
4. [Credential Configuration in n8n](#credential-configuration-in-n8n)
5. [Automated Fix Script](#automated-fix-script)
6. [Manual Configuration Steps](#manual-configuration-steps)
7. [Validation and Testing](#validation-and-testing)
8. [Troubleshooting](#troubleshooting)

---

## 🏗️ Understanding the Architecture

### Three-Layer Security Model

```
┌─────────────────────────────────────────────┐
│  WORKFLOW JSON FILES                        │
│  • Contains credential REFERENCES only      │
│  • No actual API keys                       │
│  • Safe to commit to Git                    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  n8n CREDENTIALS                            │
│  • Named credentials (e.g., "Supabase...")  │
│  • References environment variables         │
│  • Encrypted by n8n                         │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  ENVIRONMENT VARIABLES                      │
│  • Actual API keys and secrets              │
│  • Set in n8n Settings → Variables          │
│  • Never in workflow files                  │
└─────────────────────────────────────────────┘
```

### Why This Matters

- ✅ **Security**: API keys never stored in workflow JSON files
- ✅ **Portability**: Same workflows work across dev/staging/prod
- ✅ **Maintainability**: Update credentials once, affects all workflows
- ✅ **Best Practice**: Follows n8n's recommended credential management

---

## ⚙️ Supabase Node Configuration Standard

### Correct Configuration Structure

```json
{
  "parameters": {
    "resource": "row",                    // Always "row" for database operations
    "operation": "create",                // create/update/get/getAll/delete
    "tableId": "your_table_name",        // Database table name
    "dataToSend": "autoMapInputData"     // ⭐ KEY: Auto-map input to columns
  },
  "type": "n8n-nodes-base.supabase",
  "typeVersion": 1,
  "credentials": {
    "supabaseApi": {
      "id": "nw2pvY3aoD1ZsnTH",          // Credential reference ID
      "name": "Supabase - SM Agents*"    // Human-readable name
    }
  },
  "continueOnFail": true,                // Continue workflow on error
  "onError": "continueErrorOutput",      // Output error data
  "retryOnFail": true,                   // Enable automatic retries
  "maxTries": 3,                         // Retry up to 3 times
  "waitBetweenTries": 1000               // Wait 1 second between retries
}
```

### Key Configuration Points

#### 1. **dataToSend: "autoMapInputData"** ⭐
```json
"dataToSend": "autoMapInputData"
```
- **What it does**: Automatically maps input JSON properties to database columns
- **Why use it**: No manual column mapping needed - cleaner, more maintainable
- **Example**: If input is `{"name": "John", "email": "john@example.com"}`, it automatically inserts into `name` and `email` columns

#### 2. **Deprecated Syntax to Avoid** ❌
```json
// ❌ WRONG - Old syntax
"operation": "insert"

// ✅ CORRECT - New syntax
"resource": "row",
"operation": "create"
```

#### 3. **Manual Column Mapping** (Alternative - Not Recommended)
```json
// Only use if you need custom mapping
"dataToSend": "manual",
"columnsUi": {
  "columnValues": [
    {"column": "name", "value": "={{$json.fullName}}"},
    {"column": "email", "value": "={{$json.emailAddress}}"}
  ]
}
```
⚠️ **Recommendation**: Use `autoMapInputData` unless you need to transform data

---

## 🔐 Environment Variables Setup

### Required Environment Variables

Add these to your n8n instance: **Settings → Environments → Variables**

```csv
Key,Value,Usage Syntax
SUPABASE_REST_URL,https://your-project.supabase.co/rest/v1,$vars.SUPABASE_REST_URL
SUPABASE_SERVICE_ROLE_KEY,eyJhbGci...your-key-here...,$vars.SUPABASE_SERVICE_ROLE_KEY
ENVIRONMENT,production,$vars.ENVIRONMENT
```

### How to Add Variables in n8n

1. Navigate to: **Settings → Environments → Variables**
2. Click **Add Variable**
3. Enter:
   - **Key**: `SUPABASE_REST_URL`
   - **Value**: Your Supabase project URL (e.g., `https://abc123.supabase.co/rest/v1`)
4. Repeat for `SUPABASE_SERVICE_ROLE_KEY`

### Finding Your Supabase Credentials

**Supabase Dashboard:**
1. Go to: https://supabase.com/dashboard
2. Select your project
3. Navigate to: **Settings → API**
4. Copy:
   - **URL**: Under "Project URL" (add `/rest/v1` at the end)
   - **Service Role Key**: Under "Project API keys" → "service_role"

---

## 🎫 Credential Configuration in n8n

### Step 1: Create Supabase Credential

1. **Navigate**: Go to **Credentials** in n8n sidebar
2. **Create**: Click **+ Add Credential**
3. **Search**: Type "Supabase" and select "Supabase API"

### Step 2: Configure Credential Using Environment Variables

```
┌─────────────────────────────────────────────┐
│ Credential Name: Supabase - SM Agents*      │
│                                             │
│ Host:                                       │
│ {{ $vars.SUPABASE_REST_URL }}              │
│                                             │
│ Service Role Key:                           │
│ {{ $vars.SUPABASE_SERVICE_ROLE_KEY }}      │
└─────────────────────────────────────────────┘
```

**Important Notes:**
- ✅ **Name MUST match**: `Supabase - SM Agents*` (exactly as shown)
- ✅ **Use variable syntax**: `{{ $vars.VARIABLE_NAME }}`
- ✅ **No quotes needed**: n8n will evaluate the variable

### Step 3: Save and Test

1. Click **Create**
2. Test the credential using the **Test** button
3. You should see: ✅ "Credential test successful"

### Multiple Environments Setup

For dev/staging/prod, create separate credentials:

```
Supabase - SM Agents* (Production)
Supabase - SM Agents Dev
Supabase - SM Agents Staging
```

Each references different environment variables or the same variables with different values per environment.

---

## 🤖 Automated Fix Script

### Python Script to Fix All Workflows

Save this as `fix_supabase_nodes.py`:

```python
#!/usr/bin/env python3
"""
Fix all Supabase nodes in n8n workflows
- Updates operation syntax (insert → create)
- Configures Auto-Map Input Data
- Adds proper error handling and retries
- Sets consistent credentials
"""
import json
import glob
import os
import sys

def fix_supabase_node(node):
    """Fix a single Supabase node"""
    if node.get('type') != 'n8n-nodes-base.supabase':
        return node, False
    
    changed = False
    params = node.get('parameters', {})
    
    # Fix operation syntax (insert → create)
    if 'operation' in params and 'resource' not in params:
        params['resource'] = 'row'
        changed = True
    
    if params.get('operation') == 'insert':
        params['operation'] = 'create'
        changed = True
    
    # Ensure dataToSend is set to autoMapInputData
    if params.get('dataToSend') != 'autoMapInputData':
        params['dataToSend'] = 'autoMapInputData'
        # Remove manual column mappings if present
        if 'columnsUi' in params:
            del params['columnsUi']
        changed = True
    
    # Add retry logic if not present
    if 'retryOnFail' not in node:
        node['retryOnFail'] = True
        node['maxTries'] = 3
        node['waitBetweenTries'] = 1000
        changed = True
    
    # Ensure credentials are set
    if 'credentials' not in node:
        node['credentials'] = {
            "supabaseApi": {
                "id": "nw2pvY3aoD1ZsnTH",
                "name": "Supabase - SM Agents*"
            }
        }
        changed = True
    
    # Ensure error handling
    if 'continueOnFail' not in node:
        node['continueOnFail'] = True
        node['onError'] = 'continueErrorOutput'
        changed = True
    
    return node, changed

def fix_workflow(file_path):
    """Fix all Supabase nodes in a workflow"""
    print(f"Processing {os.path.basename(file_path)}...")
    
    with open(file_path, 'r') as f:
        workflow = json.load(f)
    
    total_changes = 0
    nodes = workflow.get('nodes', [])
    
    for i, node in enumerate(nodes):
        fixed_node, changed = fix_supabase_node(node)
        if changed:
            nodes[i] = fixed_node
            total_changes += 1
            print(f"  ✓ Fixed node: {node.get('name', 'Unknown')}")
    
    if total_changes > 0:
        with open(file_path, 'w') as f:
            json.dump(workflow, f, indent=2)
        print(f"  ✓ Saved {total_changes} changes")
    else:
        print(f"  • No changes needed")
    
    return total_changes

def main():
    # Adjust this path to your workflows directory
    base_path = "./workflows"  
    
    # Find all JSON files recursively
    pattern = os.path.join(base_path, "**", "*.json")
    files = glob.glob(pattern, recursive=True)
    
    if not files:
        print(f"No JSON files found in {base_path}")
        return 1
    
    print(f"Found {len(files)} workflow files")
    print("=" * 60)
    
    total_workflows_fixed = 0
    total_nodes_fixed = 0
    
    for file_path in sorted(files):
        changes = fix_workflow(file_path)
        if changes > 0:
            total_workflows_fixed += 1
            total_nodes_fixed += changes
        print()
    
    print("=" * 60)
    print(f"Summary:")
    print(f"  Workflows processed: {len(files)}")
    print(f"  Workflows fixed: {total_workflows_fixed}")
    print(f"  Nodes fixed: {total_nodes_fixed}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### How to Use the Script

```bash
# 1. Navigate to your agent directory
cd /path/to/your/agent

# 2. Update the base_path in the script to point to your workflows
# Edit line: base_path = "./workflows"

# 3. Run the script
python3 fix_supabase_nodes.py

# 4. Review the output
# The script will show which nodes were fixed in each workflow
```

---

## 📝 Manual Configuration Steps

If you prefer to configure nodes manually in n8n UI:

### Step 1: Open Workflow Node

1. Double-click the Supabase node
2. Go to **Parameters** tab

### Step 2: Configure Basic Settings

- **Resource**: Select `Row`
- **Operation**: Select your operation (Create, Update, Get, etc.)
- **Table**: Select or type your table name

### Step 3: Configure Data Mapping

- **Data to Send**: Select **"Auto-Map Input Data to Columns"**
  - This is the dropdown shown in your screenshot
  - ✅ Use this option for automatic mapping
  - ❌ Avoid "Define Below for Each Column" unless needed

### Step 4: Set Credentials

- **Credential to connect with**: Select `Supabase - SM Agents*`
- If not available, click **+ Create new credential** and follow [Credential Configuration](#credential-configuration-in-n8n)

### Step 5: Configure Error Handling (Settings Tab)

1. Click **Settings** tab
2. Enable:
   - ✅ **Continue On Fail**
   - ✅ **Retry On Fail**
   - **Max Tries**: `3`
   - **Wait Between Tries**: `1000` (ms)

### Step 6: Save

Click **Save** (outside the node editor)

---

## ✅ Validation and Testing

### Check 1: Verify Configuration

Run this command in your workflows directory:

```bash
# Count Supabase nodes
grep -r '"type": "n8n-nodes-base.supabase"' . | wc -l

# Check for deprecated syntax
grep -r '"operation": "insert"' . | wc -l
# Should return 0 if all fixed

# Check for auto-map configuration
grep -r '"dataToSend": "autoMapInputData"' . | wc -l
# Should match the Supabase node count
```

### Check 2: Test in n8n

1. Import a workflow with Supabase nodes
2. Execute the workflow
3. Verify the Supabase node shows:
   - ✅ Green checkmark (success)
   - ✅ Data inserted/retrieved correctly
   - ✅ No credential errors

### Check 3: Test Error Handling

1. Temporarily disconnect from internet or disable Supabase
2. Execute workflow
3. Verify:
   - ✅ Retry attempts show in execution log
   - ✅ Workflow continues (doesn't stop completely)
   - ✅ Error output is captured

---

## 🔧 Troubleshooting

### Problem: "Credential not found"

**Symptom**: Red error in Supabase node: "Credential with id 'xxx' not found"

**Solution**:
1. Create the credential named `Supabase - SM Agents*` in n8n
2. Or run the fix script to update credential references

### Problem: "Missing resource parameter"

**Symptom**: Workflow import fails or node shows configuration error

**Solution**:
```bash
# Run the fix script
python3 fix_supabase_nodes.py
```

### Problem: "Column does not exist"

**Symptom**: Error when inserting data: "column 'xyz' does not exist"

**Solution**:
1. Check your input data property names match database column names exactly
2. Use manual column mapping if you need to transform:
   ```json
   "dataToSend": "manual",
   "columnsUi": {
     "columnValues": [
       {"column": "db_column_name", "value": "={{$json.input_property_name}}"}
     ]
   }
   ```

### Problem: "Too many retries"

**Symptom**: Workflow takes too long, keeps retrying

**Solution**:
1. Check Supabase service status: https://status.supabase.com
2. Verify environment variables are set correctly
3. Test credential in n8n UI
4. Check network/firewall settings

### Problem: Environment variables not resolving

**Symptom**: Credential test fails, shows literal `{{ $vars.SUPABASE_REST_URL }}`

**Solution**:
1. Ensure variables are created in n8n: **Settings → Environments → Variables**
2. Variable names must match exactly (case-sensitive)
3. No quotes around variable syntax in credential fields
4. Restart n8n after adding variables (if self-hosted)

---

## 📚 Additional Resources

- **n8n Supabase Node Docs**: https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.supabase/
- **Supabase API Docs**: https://supabase.com/docs/reference/api
- **n8n Credential Management**: https://docs.n8n.io/credentials/
- **n8n Environment Variables**: https://docs.n8n.io/hosting/environment-variables/

---

## 🎯 Quick Reference Checklist

Use this when setting up a new agent:

- [ ] Environment variables configured in n8n
- [ ] Credential created: `Supabase - SM Agents*`
- [ ] Credential uses environment variables
- [ ] All Supabase nodes use native `n8n-nodes-base.supabase` node
- [ ] All nodes have `resource: "row"`
- [ ] All nodes have `dataToSend: "autoMapInputData"`
- [ ] All nodes have error handling enabled
- [ ] All nodes have retry logic (3 attempts)
- [ ] No deprecated `operation: "insert"` syntax
- [ ] Workflows tested and validated

---

**Last Updated**: October 13, 2025  
**Version**: 1.0  
**Status**: Production Ready ✅

