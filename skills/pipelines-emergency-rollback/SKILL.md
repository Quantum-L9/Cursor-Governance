---
name: pipelines-emergency-rollback
description: 🚨 Emergency Rollback Pipeline
disable-model-invocation: true
---

---
command: EMERGENCY_ROLLBACK
version: 1.0.0
category: pipeline
tags: [pipeline, emergency, rollback, disaster-recovery, production]
dependencies: [backup-versioned, workflow-validate]
risk_level: high
requires_backup: false
estimated_duration: 2-5min
---

# 🚨 Emergency Rollback Pipeline

## 📖 Purpose
Immediate recovery to last known good state when production systems fail. Fast, automated rollback with minimal downtime and comprehensive verification.

## 🎪 When to Use
- Production system failure or critical bugs
- Deployment went wrong
- Data corruption detected
- Security breach discovered
- Performance degradation severe
- **ANY critical production issue**

## ⚠️ When NOT to Use
- Minor issues that can be fixed forward
- During scheduled maintenance (use planned rollback)
- Testing/staging environments (less critical)

## 🔍 Pre-Conditions
- [ ] Critical production issue confirmed
- [ ] Backup file exists and is accessible
- [ ] Team alerted of emergency rollback
- [ ] Root cause identified (or being investigated)

## 🚀 Execution

This pipeline executes **5 RAPID steps** for emergency recovery:

---

### ⚡ Pipeline Overview
```
Step 1: Emergency Assessment (30 sec)
Step 2: Create Emergency Backup of Current State (30 sec)
Step 3: Restore from Last Good Backup (1-2 min)
Step 4: Verify Restoration (30-60 sec)
Step 5: Post-Rollback Validation (1-2 min)
```

**Total Time:** 2-5 minutes
**Priority:** MAXIMUM (all other operations paused)

---

### Step 1: Emergency Assessment (30 sec)
**Purpose:** Quick assessment of current production state

**Actions:**
1. Identify what's broken
2. Confirm backup to restore from
3. Estimate impact of rollback
4. Alert team

**Checks:**
- What workflows are failing?
- What was the last change made?
- Which backup to restore? (most recent or specific)
- Are users impacted right now?

**Output:**
```
⚠️ EMERGENCY ASSESSMENT
- Issue: Webhook timeout on all dispatch requests
- Last change: Deploy at 2025-10-01 16:30
- Backup to restore: BACKUP_20251001_160000 (pre-deployment)
- User impact: HIGH (all dispatch operations down)
- Decision: ROLLBACK IMMEDIATELY
```

---

### Step 2: Create Emergency Backup of Broken State (30 sec)
**Command:** `@backup-versioned --emergency`

**Purpose:** Preserve current (broken) state for forensic analysis

**Creates:**
- Emergency backup with `.broken` suffix
- Timestamp and error logs
- Current workflow states
- System snapshots

**File:** `Backups/EMERGENCY_BACKUP_20251001_164500.broken.tar.gz`

**Why:** Need to analyze what went wrong after recovery

---

### Step 3: Restore from Last Good Backup (1-2 min)
**Purpose:** Restore to last known working state

**Process:**
1. Stop all currently running workflows
2. Deactivate broken workflows
3. Extract backup file
4. Restore workflow JSON files
5. Re-upload to n8n production
6. Reactivate workflows

**Commands:**
```bash
# Extract backup
tar -xzf Backups/BACKUP_20251001_160000.tar.gz -C ./restore_temp/

# Restore workflows to production n8n
# (Manual or via n8n API)
```

**What Gets Restored:**
- All workflow JSON files
- Configuration files
- Sticky notes and documentation
- Workflow connections and settings

**What Doesn't Get Restored:**
- Credentials (remain as-is in n8n)
- Database data (separate recovery if needed)
- Execution history

---

### Step 4: Verify Restoration (30-60 sec)
**Purpose:** Confirm system is back to working state

**Verification Steps:**
1. ✅ All workflows uploaded successfully
2. ✅ All workflows activated
3. ✅ Webhooks responding (test endpoints)
4. ✅ First test execution successful
5. ✅ No immediate errors

**Quick Tests:**
```bash
# Test webhook endpoints
curl https://ibeylin.app.n8n.cloud/webhook/test -X POST

# Expected: 200 OK response
```

---

### Step 5: Post-Rollback Validation (1-2 min)
**Command:** `@workflow-validate`

**Purpose:** Comprehensive validation of restored system

**Validates:**
- All workflows structurally sound
- Connections intact
- Expressions valid
- Credentials still configured
- Performance acceptable

**Success Criteria:**
- ✅ All workflows passing validation
- ✅ System responding normally
- ✅ Error rate back to baseline
- ✅ Response times acceptable

---

## ✅ Post-Conditions
- [ ] Production system operational
- [ ] All workflows active and healthy
- [ ] Broken state preserved for analysis
- [ ] Team notified of rollback completion
- [ ] Incident report initiated
- [ ] Root cause analysis scheduled

## 🔗 Success Metrics
1. **Speed:** Rollback completed in < 5 minutes
2. **Completeness:** All workflows restored and functional
3. **Data Preserved:** Broken state saved for analysis
4. **Communication:** Team alerted throughout process
5. **Stability:** No new issues introduced by rollback

## 🚨 What If Rollback Fails?

### Escalation Procedure

#### Level 1: Try Previous Backup
```
If most recent backup fails, try the one before:
@emergency-rollback to BACKUP_20250930_193848
```

#### Level 2: Manual Restoration
```
1. Manually download workflows from n8n
2. Compare with backup files
3. Identify corrupted workflows
4. Manually restore working versions
```

#### Level 3: Contact n8n Support
```
1. Log into n8n cloud console
2. Contact support with backup files
3. Request manual restoration assistance
```

#### Level 4: Rebuild from Source
```
If all backups fail:
1. Use git history to restore workflow files
2. Rebuild workflows from documentation
3. Reconfigure from scratch if necessary
```

## 📊 Output Format

### Emergency Rollback Report
```markdown
# 🚨 Emergency Rollback Report
**Date:** 2025-10-01 16:45:30
**Duration:** 3 minutes 42 seconds
**Status:** ✅ SYSTEM RECOVERED

---

## Incident Summary

**Issue Detected:** 2025-10-01 16:43:00
**Rollback Initiated:** 2025-10-01 16:45:00
**System Restored:** 2025-10-01 16:48:42

**Root Cause:** Webhook timeout after production deployment
**User Impact:** HIGH (all dispatch operations affected)
**Downtime:** 5 minutes 42 seconds

---

## Rollback Execution

| Step | Action | Duration | Status |
|------|--------|----------|--------|
| 1 | Emergency assessment | 30s | ✅ COMPLETE |
| 2 | Backup broken state | 28s | ✅ SAVED |
| 3 | Restore from backup | 1m 45s | ✅ RESTORED |
| 4 | Verify restoration | 42s | ✅ VERIFIED |
| 5 | Post-rollback validation | 17s | ✅ PASSED |

**Total Time:** 3m 42s

---

## Restoration Details

### Backup Restored
**File:** `BACKUP_20251001_160000.tar.gz`
**Date:** 2025-10-01 16:00:00 (pre-deployment)
**Size:** 2.1 MB
**Workflows:** 12 workflows restored

### Emergency Backup Created
**File:** `EMERGENCY_BACKUP_20251001_164500.broken.tar.gz`
**Size:** 2.3 MB
**Purpose:** Forensic analysis of failure

### Workflows Restored
1. ✅ Linda Master Orchestrator → v2.2 (rolled back from v2.3)
2. ✅ Freight Rate Request Agent → v1.2
3. ✅ Dispatch Coordinator Agent → v2.0 (rolled back from v2.1)
4. ✅ Trucker Selector Agent → v1.5
5. ✅ Load Assignment Agent → v1.3
6. ✅ Communication Manager → v2.0
7. ✅ WhatsApp Handler → v1.8
8. ✅ SMS Handler → v1.6
9. ✅ Email Handler → v1.4
10. ✅ Reply Listener Agent → v1.2
11. ✅ Auto Responder Agent → v1.1
12. ✅ State Machine Agent → v2.0

---

## Verification Results

### System Health Check
✅ All 12 workflows active
✅ Webhooks responding (200 OK)
✅ Test executions successful
✅ Error rate: 0.1% (normal)
✅ Response times: 152ms avg (normal)

### Issues Resolved
✅ Webhook timeouts eliminated
✅ Dispatch operations functioning
✅ No error logs in past 5 minutes

---

## Next Steps

### Immediate Actions Required
1. 🔴 **Root cause analysis** - Investigate broken deployment
2. 🔴 **Review changes** - What went wrong in v2.3?
3. 🔴 **Fix and test** - Correct issues in staging
4. 🟡 **Communication** - Notify affected users

### Follow-Up Tasks
- [ ] Analyze emergency backup for root cause
- [ ] Review deployment process
- [ ] Update deployment checklist
- [ ] Test fix in staging before re-deploy
- [ ] Document lessons learned

---

## Communication

### Notifications Sent
✅ **WhatsApp** (16:45:00): "🚨 EMERGENCY: Rollback initiated due to webhook failures"
✅ **WhatsApp** (16:48:42): "✅ RESOLVED: System restored, all workflows operational"
✅ **Supabase Log**: Incident recorded with full details

### Stakeholders Notified
- Igor Beylin (+1-980-266-9595): Immediate notification
- Development team: Incident alert
- Operations: System status update

---

## Incident Classification

**Severity:** 🔴 CRITICAL
**Category:** Deployment Failure
**Impact:** Production Downtime
**Duration:** 5m 42s
**Users Affected:** All dispatch operations

---

## Lessons Learned

### What Went Wrong
- New deployment (v2.3) caused webhook timeouts
- Insufficient testing in staging environment
- No gradual rollout (deployed all at once)

### What Went Right
- Rollback executed quickly (< 4 minutes)
- Backup was recent and valid
- Team responded immediately
- No data loss

### Improvements Needed
1. **Enhanced staging testing** - More realistic load tests
2. **Gradual rollouts** - Deploy to subset first
3. **Better monitoring** - Earlier detection of issues
4. **Automated rollback** - Trigger on error threshold

---

## Post-Incident Review Scheduled
**Date:** 2025-10-02 10:00 AM
**Attendees:** Development team, Operations
**Agenda:** Root cause analysis, process improvements

---

*Emergency rollback completed by EMERGENCY_ROLLBACK pipeline v1.0.0*
*System operational and stable*
```

## 🔗 Combines Well With

### Before This Pipeline
- **Detection** → **EMERGENCY_ROLLBACK** (system monitoring detects issue)

### After This Pipeline
- **EMERGENCY_ROLLBACK** → **@workflow-diff** (analyze what changed)
- **EMERGENCY_ROLLBACK** → **@thinking-mode** (root cause analysis)
- **EMERGENCY_ROLLBACK** → Fix → **@deploy-production** (re-deploy when fixed)

## 💡 Pro Tips

### Tip 1: Don't Hesitate
If production is broken, rollback immediately. Fix and redeploy later.

### Tip 2: Preserve Broken State
Always backup current state before rollback for analysis.

### Tip 3: Communicate Constantly
Keep team and stakeholders informed throughout rollback.

### Tip 4: Test Backups Regularly
Verify backups are restorable BEFORE you need them.

### Tip 5: Document Everything
Record exact timeline and actions for incident report.

### Tip 6: Learn from Every Incident
Conduct post-mortem and implement improvements.

## 🔖 Examples

### Example 1: Quick Recovery
```
User: "@emergency-rollback to last backup"
AI:
  🚨 EMERGENCY ROLLBACK INITIATED
  
  [1/5] Assessment: Critical webhook failure detected
  [2/5] Emergency backup created: EMERGENCY_BACKUP_20251001.broken.tar.gz
  [3/5] Restoring from: BACKUP_20251001_160000.tar.gz
  [4/5] Verification: All workflows restored and active
  [5/5] Validation: System healthy and operational
  
  ✅ ROLLBACK COMPLETE (3m 42s)
  📊 Downtime: 5m 42s
  📱 Team notified
  🔍 Broken state preserved for analysis
```

### Example 2: Specific Backup
```
User: "@emergency-rollback to BACKUP_20250930_193848"
AI:
  🚨 EMERGENCY ROLLBACK INITIATED
  Target: BACKUP_20250930_193848 (1 day old)
  
  [Executing rollback...]
  ✅ COMPLETE (4m 15s)
  
  ⚠️ Note: Rolled back 1 day - recent changes lost
  📋 Review what was between then and now
```

---

## 📚 Related Commands
- `backup-versioned` - Create backups (prevention)
- `workflow-validate` - Validate after rollback
- `workflow-diff` - Analyze what changed
- `deploy-production` - Re-deploy after fix
- `thinking-mode` - Root cause analysis

## 📝 Version History
- **1.0.0** (2025-10-01): Initial emergency rollback pipeline with 5-step recovery

---

*Command Standard Version: 2.0.0*
*Pipeline Type: Emergency Response*
*Priority: CRITICAL*

