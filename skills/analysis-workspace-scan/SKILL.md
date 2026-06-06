---
name: analysis-workspace-scan
description: 📁 Comprehensive Workspace Scanner
disable-model-invocation: true
---

---
command: WORKSPACE_SCAN
version: 1.1.0
category: analysis
tags: [analysis, structure, organization, overview]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: 1-2min
---

# 📁 Comprehensive Workspace Scanner

## 📖 Purpose
Analyze workspace structure, organization, and file distribution. Generate recommendations for improvements and restructuring.

## 🚀 Execution

**Analyzes:**
- Directory structure and organization
- File count by category
- Workflow distribution
- Documentation coverage
- Script and configuration presence
- Backup status

**Output:**
```
📁 Workspace Structure Analysis

Total Files: 145
├── Workflows: 12 (organized by function)
├── Documentation: 20 files (excellent coverage)
├── Scripts: 8 (deployment & utilities)
├── Configuration: 5 files
├── Data Files: 15 (CSV, Excel)
└── Backups: 4 (current, good retention)

Organization Score: 8.5/10 (WELL ORGANIZED)

Structure Quality:
✅ Clear folder hierarchy
✅ Workflows categorized properly
✅ Documentation comprehensive
✅ Scripts organized
⚠️ Consider archiving 2 old files

Recommendations:
1. Add README to Testing/ folder
2. Archive backups older than 4 weeks
3. Consider separating staging/prod configs
```

---

*Command Standard Version: 2.0.0*

