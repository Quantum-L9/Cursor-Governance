---
name: n8n-node-update
description: 🔄 Deprecated Node Updater
disable-model-invocation: true
---

---
command: NODE_UPDATE_DEPRECATED
version: 1.0.0
category: n8n
tags: [maintenance, deprecated, updates, n8n]
dependencies: []
risk_level: moderate
requires_backup: true
estimated_duration: 2-3min
---

# 🔄 Deprecated Node Updater

## 📖 Purpose
Check all n8n nodes against documentation, identify deprecated nodes, and update to current versions or flag for manual review.

## 🚀 Execution

**Actions:**
1. Scan all workflows for nodes
2. Check against n8n documentation
3. Identify deprecated nodes
4. Auto-update safe version bumps
5. Flag breaking changes for review
6. Update sticky notes with instructions

**Output:**
```
🔄 Node Update Check

Workflows Scanned: 12
Deprecated Nodes Found: 3

Auto-Updated (safe):
✅ HTTP Request v1 → v2 (2 workflows)

Flagged for Manual Review:
⚠️ Function Node → Code Node (1 workflow)
   - Breaking change in API
   - Review required before update

Status: 2 updated, 1 needs review
```

---

*Command Standard Version: 2.0.0*

