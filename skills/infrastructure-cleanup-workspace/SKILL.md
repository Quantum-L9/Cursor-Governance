---
name: infrastructure-cleanup-workspace
description: 🧹 Intelligent Workspace Cleanup
disable-model-invocation: true
---

---
command: CLEANUP_WORKSPACE
version: 1.1.0
category: infrastructure
tags: [cleanup, maintenance, organization, disk-space]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: 1-2min
---

# 🧹 Intelligent Workspace Cleanup

## 📖 Purpose
Remove temporary files, duplicates, and clutter while preserving important files. Frees disk space and improves organization.

## 🎪 When to Use
- Weekly maintenance
- Before deployments
- When workspace feels cluttered
- Disk space running low
- After major development sessions

## 🚀 Execution

**Removes:**
- Temporary files (*.tmp, *.temp, *.swp)
- Python cache (__pycache__, *.pyc)
- OS artifacts (.DS_Store, Thumbs.db)
- Old log files (>30 days)
- Duplicate workflow files
- Empty directories

**Preserves:**
- All production workflows
- Recent logs (<30 days)
- Backups folder
- Documentation
- Configuration files
- Data files

**Output:**
```
🧹 Workspace Cleanup Complete

Removed:
- 45 temporary files (12 MB)
- 8 old log files (3 MB)
- 3 Python cache directories
- 12 OS artifacts
- 0 duplicates found

💾 Total space freed: 15.3 MB
📊 Cleanup ratio: 92% current, 8% removed
```

## ✅ Success Metrics
- ✅ Temp files removed
- ✅ No duplicates
- ✅ Disk space freed
- ✅ Workspace organized

---

*Command Standard Version: 2.0.0*

