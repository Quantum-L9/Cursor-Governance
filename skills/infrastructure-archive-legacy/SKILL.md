---
name: infrastructure-archive-legacy
description: 📦 Legacy File Archiver
disable-model-invocation: true
---

---
command: ARCHIVE_LEGACY
version: 1.1.0
category: infrastructure
tags: [archival, organization, maintenance, cleanup]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: 1-2min
---

# 📦 Legacy File Archiver

## 📖 Purpose
Auto-detect and archive outdated workflow versions and legacy files to keep workspace clean while preserving history.

## 🎪 When to Use
- Weekly/monthly maintenance
- After major version updates
- Before production deployments
- When workspace feels cluttered
- Project cleanup sessions

## 🚀 Execution

**Detects Legacy Files:**
- Workflows not modified in 90+ days
- Files with "old", "deprecated", "test" in name
- Workflows with version numbers < current
- Workflows never referenced by others
- Duplicate workflow versions

**Archives To:**
`Archive/YYYY/MM/` directory structure

**Preserves:**
- File modification dates
- Original directory structure
- Metadata and documentation

**Output:**
```
📦 Legacy File Archival

Files Detected: 3
✅ Old_Rate_Calculator_v1.0.json → Archive/2025/10/
✅ Test_Communication_Handler.json → Archive/2025/10/
✅ Deprecated_Workflow_Manager.json → Archive/2025/10/

Files Archived: 3
Current Files: 12
Archive Ratio: 92% current, 8% archived

Workspace Status: CLEAN AND ORGANIZED
```

## ✅ Success Metrics
- ✅ Legacy files identified
- ✅ Files archived safely
- ✅ No production files affected
- ✅ History preserved

---

*Command Standard Version: 2.0.0*

