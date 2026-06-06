---
name: pipelines-_legacy-weekly-maintenance
description: 🧹 Weekly Maintenance Pipeline
disable-model-invocation: true
---

---
command: WEEKLY_MAINTENANCE
version: 1.0.0
category: pipeline
tags: [pipeline, maintenance, automation, scheduled, cleanup]
dependencies: [backup-versioned, cleanup-workspace, archive-legacy, node-update, security-audit, dependency-map]
risk_level: safe
requires_backup: true
estimated_duration: 10-15min
---

# 🧹 Weekly Maintenance Pipeline

## 📖 Purpose
Automated weekly maintenance routine to keep the system clean, secure, and optimized. Runs regular housekeeping tasks, updates, backups, and health checks.

## 🎪 When to Use
- Every Sunday at 2:00 AM (automated schedule)
- Before major deployments
- After completing major features
- When system feels cluttered
- Monthly comprehensive maintenance

## ⚠️ When NOT to Use
- During active development
- During business hours (use off-hours)
- When system is unstable (fix first)

## 🔍 Pre-Conditions
- [ ] No active deployments in progress
- [ ] System in stable state
- [ ] No critical issues pending
- [ ] Scheduled during low-traffic period

## 🚀 Execution

This pipeline executes **7 maintenance steps** for system hygiene:

---

### 🗓️ Pipeline Overview
```
Step 1: Weekly Backup
Step 2: Workspace Cleanup
Step 3: Archive Legacy Files
Step 4: Update Deprecated Nodes
Step 5: Security Audit
Step 6: Update Architecture Docs
Step 7: Health Report Generation
```

---

### Step 1: Weekly Backup (30-60 sec)
**Command:** `@backup-versioned --weekly`

**Purpose:** Create regular weekly backup for disaster recovery

**Creates:**
- Timestamped backup: `BACKUP_WEEKLY_YYYYMMDD.tar.gz`
- Stored in `Backups/Weekly/` directory
- Retention: Keep last 4 weeks (monthly rotation)

**What Gets Backed Up:**
- All workflow JSON files
- Configuration files
- Documentation
- Scripts
- Data files (if applicable)

**Success Criteria:**
- ✅ Backup file created successfully
- ✅ Size > 1MB (non-empty)
- ✅ Backup manifest generated
- ✅ Previous backups rotated (delete > 4 weeks old)

**Output:**
```
✅ Weekly backup created: BACKUP_WEEKLY_20251006.tar.gz (2.4 MB)
📦 Retained backups: 4 weeks
🗑️ Deleted: 1 backup older than 4 weeks
```

---

### Step 2: Workspace Cleanup (1-2 min)
**Command:** `@cleanup-workspace`

**Purpose:** Remove temporary files, duplicates, and unnecessary clutter

**Cleans:**
- Temporary files (`*.tmp`, `*.temp`, `*.swp`)
- Log files older than 30 days
- Duplicate workflow files
- Empty directories
- Python cache (`__pycache__`, `*.pyc`)
- OS artifacts (`.DS_Store`)

**Preserves:**
- All production workflow files
- Recent logs (< 30 days)
- Backups folder
- Documentation
- Configuration files

**Success Criteria:**
- ✅ All temp files removed
- ✅ No duplicate workflows found
- ✅ Disk space freed up
- ✅ Workspace organized

**Output:**
```
🧹 Cleanup complete:
- Removed 45 temporary files (12 MB freed)
- Deleted 8 old log files
- Cleaned 3 Python cache directories
- Removed 12 OS artifacts
💾 Total space freed: 15.3 MB
```

---

### Step 3: Archive Legacy Files (1-2 min)
**Command:** `@archive-legacy`

**Purpose:** Auto-detect and archive outdated workflow versions

**Detects:**
- Workflows not modified in 90+ days
- Workflows with "old", "deprecated", "test" in name
- Workflows with version numbers < current
- Workflows never referenced by others

**Archives To:** `Archive/YYYY/MM/` directory structure

**Preserves:**
- File modification dates
- Original directory structure
- Metadata and documentation

**Success Criteria:**
- ✅ Legacy files identified
- ✅ Files moved to Archive folder
- ✅ Archive organized by date
- ✅ No production files archived accidentally

**Output:**
```
📦 Legacy files archived:
- Old_Rate_Calculator_v1.0.json → Archive/2025/10/
- Test_Communication_Handler.json → Archive/2025/10/
- Deprecated_Workflow_Manager.json → Archive/2025/10/
📊 3 files archived (cleanup ratio: 92% current, 8% archived)
```

---

### Step 4: Update Deprecated Nodes (2-3 min)
**Command:** `@node-update`

**Purpose:** Update or flag deprecated n8n nodes

**Checks:**
- All nodes in all workflows
- Compares against n8n documentation
- Identifies deprecated nodes
- Suggests current replacements

**Actions:**
- **Auto-update:** Safe node version bumps
- **Flag for review:** Breaking changes needed
- **Document:** Sticky notes with update instructions

**Success Criteria:**
- ✅ All workflows scanned
- ✅ Deprecated nodes identified
- ✅ Safe updates applied automatically
- ✅ Manual updates flagged

**Output:**
```
🔄 Node update complete:
- 12 workflows scanned
- 3 deprecated nodes found
- 2 auto-updated (safe version bumps)
- 1 flagged for manual review (breaking change)

⚠️ Manual Review Needed:
- Workflow: "Dispatch Coordinator"
- Node: HTTP Request (v1) → (v2)
- Change: Authentication method updated
- Action: Review and update manually
```

---

### Step 5: Security Audit (2-3 min)
**Command:** `@security-audit`

**Purpose:** Weekly security scan for vulnerabilities

**Scans For:**
- Exposed API keys or credentials
- Hardcoded secrets
- Insecure webhook endpoints
- SQL injection risks
- Outdated dependencies
- Permission issues

**Success Criteria:**
- ✅ Zero critical vulnerabilities
- ✅ No exposed credentials
- ✅ All endpoints secured
- ✅ No new security issues

**Output:**
```
🔒 Security audit complete:

Critical Issues: 0
High Priority: 0
Medium Priority: 1
Low Priority: 3

📋 Medium Priority:
- Webhook endpoint lacks rate limiting (non-critical)

📋 Low Priority Recommendations:
- Add HTTPS enforcement to 2 endpoints
- Update error messages to be less verbose
- Consider adding API request logging

✅ Overall Security Status: GOOD
```

---

### Step 6: Update Architecture Docs (2-3 min)
**Command:** `@dependency-map`

**Purpose:** Keep architecture documentation current

**Generates:**
- Updated dependency map
- Workflow relationship diagram
- System architecture overview
- Critical path analysis

**Updates:**
- Documentation/Architecture/ folder
- README files with current stats
- Workflow count and relationships

**Success Criteria:**
- ✅ Dependency map generated
- ✅ All workflows mapped
- ✅ Documentation updated
- ✅ Diagrams current

**Output:**
```
🗺️ Architecture documentation updated:
- 12 workflows mapped
- 27 dependencies identified
- 3 critical paths documented
- 0 circular dependencies detected
- 2 orphaned workflows flagged

📊 System Metrics:
- Total workflows: 12
- Avg complexity: 6.5/10
- Maintainability: 8.2/10
- Documentation coverage: 95%
```

---

### Step 7: Health Report Generation (1-2 min)
**Command:** `@performance-profile` (if available) or custom health check

**Purpose:** Generate weekly system health report

**Monitors:**
- Workflow execution counts
- Average execution times
- Error rates
- Resource usage
- API call statistics

**Generates:**
- Weekly health report
- Trend analysis
- Performance recommendations

**Success Criteria:**
- ✅ Health report generated
- ✅ All metrics within normal range
- ✅ No performance degradation detected
- ✅ Recommendations documented

**Output:**
```
📊 Weekly Health Report (Sep 30 - Oct 6):

Execution Stats:
- Total executions: 3,482
- Successful: 3,461 (99.4%)
- Failed: 21 (0.6%)
- Avg execution time: 2.3s

Performance:
- Webhook response: 148ms avg (good)
- Database queries: 1.9s avg (good)
- API calls: 315ms avg (excellent)

Trends:
📈 Execution count: +12% vs last week
📉 Error rate: -0.2% (improvement)
📊 Performance: Stable

Recommendations:
- None this week - system healthy!
```

---

## ✅ Post-Conditions
- [ ] Weekly backup created and verified
- [ ] Workspace cleaned and organized
- [ ] Legacy files archived
- [ ] Deprecated nodes updated or flagged
- [ ] Security audit passed
- [ ] Documentation updated
- [ ] Health report generated and reviewed

## 🔗 Success Metrics
1. **Backup Success:** Weekly backup created and verified
2. **Space Freed:** Minimum 10MB disk space reclaimed
3. **Security:** Zero new critical vulnerabilities
4. **Documentation:** 100% current and accurate
5. **Performance:** All metrics within acceptable range

## 📊 Output Format

### Weekly Maintenance Report
```markdown
# 🧹 Weekly Maintenance Report
**Week:** October 1-7, 2025
**Execution Date:** Sunday, October 6, 2025 02:00 AM
**Duration:** 12 minutes 35 seconds
**Status:** ✅ COMPLETED SUCCESSFULLY

---

## Maintenance Summary

| Step | Task | Duration | Status | Details |
|------|------|----------|--------|---------|
| 1 | Weekly Backup | 48s | ✅ | 2.4 MB backup created |
| 2 | Workspace Cleanup | 1m 42s | ✅ | 15.3 MB freed |
| 3 | Archive Legacy | 1m 28s | ✅ | 3 files archived |
| 4 | Update Nodes | 2m 45s | ⚠️ | 1 manual review needed |
| 5 | Security Audit | 2m 58s | ✅ | 0 critical issues |
| 6 | Update Docs | 2m 12s | ✅ | Architecture updated |
| 7 | Health Report | 1m 42s | ✅ | System healthy |

**Total Duration:** 12m 35s
**Overall Status:** ✅ ALL TASKS COMPLETE

---

## Key Findings

### ✅ Successes
- System running smoothly (99.4% success rate)
- No critical security issues
- Documentation 100% current
- Performance within target ranges

### ⚠️ Items for Review
- 1 deprecated node needs manual update (non-urgent)
- 3 workflow files could be archived next month
- Consider adding rate limiting to 1 webhook

### 📈 Improvements This Week
- Error rate decreased by 0.2%
- Execution speed improved by 50ms avg
- Freed 15.3 MB disk space

---

## Next Week's Focus
1. Review and update flagged deprecated node
2. Monitor error rate trend (improving)
3. Consider implementing suggested security enhancements
4. Continue monitoring performance metrics

---

## System Health Score: 9.2/10
**Excellent** - System is well-maintained and operating optimally

---

*Maintenance completed by WEEKLY_MAINTENANCE pipeline v1.0.0*
*Next scheduled: Sunday, October 13, 2025 02:00 AM*
```

## 🔗 Combines Well With

### Before This Pipeline
- Nothing (runs independently on schedule)

### After This Pipeline
- **WEEKLY_MAINTENANCE** → review report → address flagged items

### Parallel Operations
Can run alongside other non-critical tasks.

## 💡 Pro Tips

### Tip 1: Schedule During Low Traffic
Run at 2 AM Sunday when system usage is lowest.

### Tip 2: Review Reports Monday Morning
Start your week by reviewing the maintenance report.

### Tip 3: Automate Fully
Set up cron job or n8n workflow to run automatically.

### Tip 4: Keep 4 Weeks of Backups
Balance between safety and storage space.

### Tip 5: Act on Flagged Items Promptly
Don't let technical debt accumulate.

### Tip 6: Track Trends Over Time
Compare week-over-week to spot patterns.

## 🔖 Examples

### Example 1: Automated Execution
```
[System] Cron job triggered at 2:00 AM
[Pipeline] WEEKLY_MAINTENANCE initiated automatically

[Step 1/7] Creating weekly backup... ✅ DONE (48s)
[Step 2/7] Cleaning workspace... ✅ DONE (1m 42s)
[Step 3/7] Archiving legacy files... ✅ DONE (1m 28s)
[Step 4/7] Updating nodes... ⚠️ 1 FLAGGED (2m 45s)
[Step 5/7] Security audit... ✅ DONE (2m 58s)
[Step 6/7] Updating docs... ✅ DONE (2m 12s)
[Step 7/7] Health report... ✅ DONE (1m 42s)

✅ MAINTENANCE COMPLETE (12m 35s)
📊 Report saved: reports/weekly_maintenance_20251006.md
📱 Notification sent to team (summary)
```

### Example 2: Manual Execution
```
User: "@weekly-maintenance run now"
AI:
  🧹 Starting weekly maintenance pipeline...
  
  [Executing all 7 steps...]
  
  ✅ COMPLETE (12m 35s)
  📊 Report generated
  
  Key findings:
  - System healthy (9.2/10)
  - 1 item needs review (non-urgent)
  - 15.3 MB freed
```

---

## 📚 Related Commands
- `backup-versioned` - Step 1 (backup)
- `cleanup-workspace` - Step 2 (cleanup)
- `archive-legacy` - Step 3 (archive)
- `node-update` - Step 4 (update)
- `security-audit` - Step 5 (security)
- `dependency-map` - Step 6 (docs)

## 📝 Version History
- **1.0.0** (2025-10-01): Initial weekly maintenance pipeline with 7-step routine

---

*Command Standard Version: 2.0.0*
*Pipeline Type: Scheduled Maintenance*
*Recommended Schedule: Weekly (Sunday 2 AM)*

