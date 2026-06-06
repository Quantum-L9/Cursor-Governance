---
name: n8n-clean-emojis
description: 🧹 Clean Emojis from N8N Workflows
disable-model-invocation: true
---

---
command: CLEAN_N8N_EMOJIS
version: 1.0.0
category: n8n
tags: [validation, cleanup, preprocessing, emoji-removal]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: <30sec
---

# 🧹 Clean Emojis from N8N Workflows

## 📖 Purpose
Automatically detect and remove emojis from n8n workflow JSON files before import. Fixes connection errors caused by emoji mismatches.

## 🎪 When to Use
- **ALWAYS** before importing n8n workflows
- Before deploying workflows to n8n
- When workflow connections aren't working
- As part of workflow-validate pipeline

## 🚀 Execution

**Auto-detects and fixes:**
- ✅ Emojis in node names
- ✅ Emojis in connection references
- ✅ Mismatched node name references
- ✅ Creates clean backup copy

**Preserves:**
- ✅ Emojis in notes/documentation
- ✅ All node functionality
- ✅ Original file (creates .CLEAN version)

## 💻 Implementation

```python
import json
import re
from pathlib import Path

def remove_emojis(text):
    """Remove all non-ASCII characters (emojis)"""
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()

def clean_n8n_workflow(input_file):
    """Clean emojis from n8n workflow JSON"""
    
    # Read workflow
    with open(input_file, 'r') as f:
        workflow = json.load(f)
    
    # Remove emojis from node names
    for node in workflow['nodes']:
        node['name'] = remove_emojis(node['name'])
    
    # Rebuild connections with cleaned names
    new_connections = {}
    for old_key, value in workflow['connections'].items():
        new_key = remove_emojis(old_key)
        new_value = {}
        
        for output_type, connections_array in value.items():
            cleaned_connections = []
            for conn_group in connections_array:
                cleaned_group = []
                for conn in conn_group:
                    if isinstance(conn, dict):
                        cleaned_conn = conn.copy()
                        if 'node' in cleaned_conn:
                            cleaned_conn['node'] = remove_emojis(cleaned_conn['node'])
                        cleaned_group.append(cleaned_conn)
                cleaned_connections.append(cleaned_group)
            new_value[output_type] = cleaned_connections
        
        new_connections[new_key] = new_value
    
    workflow['connections'] = new_connections
    
    # Save cleaned version
    output_file = input_file.replace('.json', '_CLEAN.json')
    with open(output_file, 'w') as f:
        json.dump(workflow, f, indent=2)
    
    return output_file

# Execute
input_file = "path/to/workflow.json"
output_file = clean_n8n_workflow(input_file)
print(f"✅ Cleaned workflow: {output_file}")
```

## 📋 Usage Examples

### Example 1: Single File
```bash
@clean-n8n-emojis path/to/workflow.json
```

### Example 2: All Files in Directory
```bash
@clean-n8n-emojis Sub_Agents/**/*.json
```

### Example 3: Before Import
```bash
@clean-n8n-emojis workflow.json && @n8n-import workflow_CLEAN.json
```

## 🔗 Integrates With

### Before This Command
- Any workflow creation/editing

### After This Command
- **@workflow-validate** (validate cleaned workflow)
- n8n import (via API or UI)

### In Pipelines
```yaml
PIPELINE_EXECUTE [
  clean-n8n-emojis,
  workflow-validate,
  n8n-deploy
]
```

## ✅ Success Output

```
🧹 Cleaning N8N Workflow Emojis

Input: 03_Freight_Rate_Request_Agent_v1.2.json
Nodes: 34
  - ✅ Cleaned 34 node names
  - ✅ Updated 29 connections

Output: 03_Freight_Rate_Request_Agent_v1.2_CLEAN.json

Status: READY FOR IMPORT
```

## 🚨 Auto-Run Scenarios

This command runs AUTOMATICALLY when:
- ✅ Importing any .json file to n8n
- ✅ Running @workflow-validate
- ✅ Running @deploy-production pipeline
- ✅ User says "import to n8n"

---

*Command Standard Version: 2.0.0*
