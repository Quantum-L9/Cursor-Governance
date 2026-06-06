---
name: infrastructure-backup-versioned
description: 💾 Versioned Backup Creator
disable-model-invocation: true
---

---
command: BACKUP_VERSIONED
version: 1.1.0
category: infrastructure
tags: [backup, disaster-recovery, versioning, safety]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: <1min
---

# 💾 Versioned Backup Creator

## 📖 Purpose
Create timestamped, versioned backups of entire workspace with manifest for disaster recovery and rollback capability.

## 🎪 When to Use
- Before ANY risky operation (deployments, major changes)
- Weekly scheduled backups
- Before credential rotation
- Pre-integration of new workflows
- After major milestones

## 🚀 Execution

**Creates:**
- **Recent backups** (< 2 days): Uncompressed directory `Backups/BACKUP_YYYYMMDD_HHMMSS/` for quick access
- **Older backups** (> 2 days): Compressed to `.tar.gz` for space savings
- Backup manifest: `BACKUP_MANIFEST.txt`
- Retention: Keeps last 4 weeks of backups

**What Gets Backed Up:**
- All workflow JSON files
- Configuration files
- Scripts
- Documentation
- Data files (CSV, Excel)
- NOT: logs, temp files, node_modules, previous backups

**Smart Compression Strategy:**
1. New backup → uncompressed directory (quick access)
2. After 2 days → auto-compress to .tar.gz (save space)
3. After 4 weeks → auto-delete (retention policy)

**Output:**
```
💾 Backup created: BACKUP_20251001_163000/ (3.4 MB uncompressed)
📦 Files: 128 backed up
✅ Recent backups: 2 uncompressed (quick access)
✅ Older backups: 2 compressed (space saving)
🗜️  Auto-compressed: 1 backup older than 2 days
🗑️  Cleaned up: 1 backup older than 4 weeks
```

## ✅ Success Metrics
- ✅ Backup file created (size > 1MB)
- ✅ Manifest complete
- ✅ Backup is restorable

---

*Command Standard Version: 2.0.0*

