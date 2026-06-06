---
name: n8n-workflow-validate
description: ✅ N8N Workflow Validator
disable-model-invocation: true
---

---
command: WORKFLOW_VALIDATE
version: 1.0.0
category: n8n
tags: [validation, n8n, quality-assurance, pre-deployment]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: 1-2min
---

# ✅ N8N Workflow Validator

## 📖 Purpose
Comprehensive validation of n8n workflows checking JSON structure, node configuration, expressions, connections, and credentials.

## 🚀 Execution

**Step 1: Auto-Clean (runs first)**
```python
python3 scripts/clean_n8n_emojis.py <workflow.json>
# Creates: <workflow>_CLEAN.json
```

**Step 2: Validates:**
- ✅ JSON structure correctness
- ✅ Node configuration completeness
- ✅ Expression syntax validity
- ✅ Connection integrity
- ✅ Credential references exist
- ✅ No deprecated nodes
- ✅ Parameter completeness
- ✅ **NO EMOJIS in node names** (auto-cleaned in Step 1)

**Output:**
```
✅ Workflow Validation Complete

Workflow: Linda Master Orchestrator
Nodes: 15 (all valid)
Connections: 24 (all valid)
Expressions: 32 (all syntactically correct)
Credentials: 5 (all referenced correctly)

Status: VALID - Ready for deployment
Issues: 0 critical, 0 warnings
```

---

*Command Standard Version: 2.0.0*

