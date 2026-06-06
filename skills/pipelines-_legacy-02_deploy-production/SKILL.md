---
name: pipelines-_legacy-02_deploy-production
description: 🚀 Production Deployment Pipeline
disable-model-invocation: true
---

---
command: DEPLOY_TO_PRODUCTION
version: 1.0.0
category: pipeline
tags: [pipeline, deployment, production, orchestration, n8n]
dependencies: [audit-full, backup-versioned, workflow-validate, credentials-manage, security-audit, workflow-deploy, performance-profile]
risk_level: high
requires_backup: true
estimated_duration: 15-20min
---

# 🚀 Production Deployment Pipeline

## 📖 Purpose
Execute a complete, safe production deployment with comprehensive validation, backup, security checks, and post-deployment monitoring. This orchestrated pipeline ensures zero-downtime deployments with automatic rollback on failure.

## 🎪 When to Use
- Deploying new workflows to production
- Pushing major updates to live systems
- Promoting from staging to production
- Monthly production updates

## ⚠️ When NOT to Use
- Dev or staging deployments (use simpler process)
- Experimental features (test in dev first)
- Emergency hotfixes (use @emergency-rollback then redeploy)

## 🔍 Pre-Conditions
- [ ] All workflows validated in staging environment
- [ ] Change management approval obtained
- [ ] Team notified of deployment window
- [ ] Rollback plan documented
- [ ] Current production state is stable

## 🚀 Execution

This pipeline executes **7 sequential steps** with automatic rollback on failure:

---

### 📊 Pipeline Overview
```
Step 1: Pre-Deployment Audit
Step 2: Safety Backup
Step 3: Workflow Validation
Step 4: Credentials Check
Step 5: Security Audit
Step 6: Deploy Workflows
Step 7: Post-Deployment Health Check
```

---

### Step 1: Pre-Deployment Audit (3-5 min)
**Command:** `@audit-full`

**Purpose:** Complete system audit to verify production readiness

**Checks:**
- All workflows have valid JSON structure
- No placeholder values or TODO comments
- All required files present
- No duplicate workflows
- Documentation up to date

**Success Criteria:**
- ✅ Zero critical issues found
- ✅ All workflows ready for deployment
- ✅ All dependencies resolved

**On Failure:** ABORT deployment, fix issues first

---

### Step 2: Safety Backup (30-60 sec)
**Command:** `@backup-versioned`

**Purpose:** Create timestamped backup of current production state

**Creates:**
- Complete workspace backup
- Backup manifest file
- Timestamp: `BACKUP_YYYYMMDD_HHMMSS`
- Stored in `Backups/` directory

**Success Criteria:**
- ✅ Backup file created (size > 1MB)
- ✅ Manifest contains all files
- ✅ Backup is restorable

**On Failure:** ABORT deployment (cannot proceed without backup)

---

### Step 3: Workflow Validation (1-2 min)
**Command:** `@workflow-validate`

**Purpose:** Validate all n8n workflows before deployment

**Validates:**
- JSON structure correctness
- Node configuration validity
- Expression syntax
- Credential references exist
- Connection integrity
- No deprecated nodes (or flagged for update)

**Success Criteria:**
- ✅ All workflows pass validation
- ✅ Zero syntax errors
- ✅ All credentials available
- ✅ No breaking changes detected

**On Failure:** ROLLBACK to backup, fix workflows

---

### Step 4: Credentials Management (30-60 sec)
**Command:** `@credentials-manage`

**Purpose:** Verify all API credentials and environment variables

**Verifies:**
- All required credentials exist
- No placeholder API keys
- Credentials have proper permissions
- Environment variables set correctly
- Production credentials (not dev)

**Success Criteria:**
- ✅ All credentials validated
- ✅ Zero placeholders found
- ✅ Proper production credentials configured

**On Failure:** ABORT deployment, update credentials

---

### Step 5: Security Audit (2-3 min)
**Command:** `@security-audit`

**Purpose:** Deep security scan before going live

**Scans For:**
- Exposed API keys or tokens
- Hardcoded credentials
- Unsecured webhook endpoints
- SQL injection vulnerabilities
- Insecure data handling
- Missing error handling

**Success Criteria:**
- ✅ Zero critical vulnerabilities
- ✅ No exposed credentials
- ✅ All endpoints secured
- ✅ Error handling present

**On Failure:** ABORT deployment, fix security issues

---

### Step 6: Deploy Workflows (5-10 min)
**Command:** `@workflow-deploy` (or manual n8n deployment)

**Purpose:** Deploy validated workflows to production n8n instance

**Process:**
1. Connect to production n8n: `https://ibeylin.app.n8n.cloud`
2. Upload workflow JSON files
3. Activate workflows one by one
4. Verify each activation successful
5. Test webhook endpoints

**Success Criteria:**
- ✅ All workflows uploaded successfully
- ✅ All workflows activated
- ✅ Webhooks responding (200 OK)
- ✅ First execution successful

**On Failure:** ROLLBACK immediately using backup

---

### Step 7: Post-Deployment Health Check (1-2 min)
**Command:** `@performance-profile`

**Purpose:** Verify system health after deployment

**Monitors:**
- Workflow execution times
- Error rates
- Webhook response times
- Database connections
- API call success rates
- Memory/CPU usage

**Success Criteria:**
- ✅ All workflows executing normally
- ✅ Error rate < 1%
- ✅ Response times within acceptable range
- ✅ No immediate failures detected

**On Warning:** Monitor closely for 1 hour
**On Failure:** ROLLBACK to previous version

---

## ✅ Post-Conditions
- [ ] All workflows deployed and active
- [ ] Health metrics within normal range
- [ ] Backup created and verified
- [ ] Team notified of successful deployment
- [ ] Monitoring alerts active
- [ ] Deployment logged in system

## 🔗 Success Metrics
1. **Zero Downtime:** No service interruption during deployment
2. **All Steps Pass:** 7/7 pipeline steps complete successfully
3. **Performance Maintained:** Response times within 10% of baseline
4. **Error-Free:** No errors in first 100 executions
5. **Rollback Ready:** Backup verified and restoration tested

## 🚨 Error Handling & Rollback

### Automatic Rollback Triggers
Pipeline will automatically rollback if:
- Any step fails with critical error
- Security vulnerabilities detected
- Validation fails
- Credentials missing or invalid
- Post-deployment health check fails

### Rollback Procedure
```yaml
1. STOP: Halt deployment immediately
2. ALERT: Notify team via WhatsApp (+1-980-266-9595)
3. RESTORE: Execute @emergency-rollback with latest backup
4. VERIFY: Confirm production restored to working state
5. INVESTIGATE: Analyze failure logs
6. FIX: Address root cause
7. RETRY: Re-run deployment after fixes
```

### Manual Rollback Command
```
@emergency-rollback to BACKUP_YYYYMMDD_HHMMSS
```

## 📊 Output Format

### Deployment Report
```markdown
# Production Deployment Report
**Date:** 2025-10-01 16:30:00
**Duration:** 18 minutes 42 seconds
**Status:** ✅ SUCCESS

---

## Pipeline Execution Summary

| Step | Command | Duration | Status | Details |
|------|---------|----------|--------|---------|
| 1 | audit-full | 3m 15s | ✅ PASS | 0 critical issues |
| 2 | backup-versioned | 45s | ✅ PASS | Backup size: 2.3 MB |
| 3 | workflow-validate | 1m 30s | ✅ PASS | 12 workflows validated |
| 4 | credentials-manage | 52s | ✅ PASS | 7 credentials verified |
| 5 | security-audit | 2m 48s | ✅ PASS | 0 vulnerabilities |
| 6 | workflow-deploy | 8m 20s | ✅ PASS | 12 workflows deployed |
| 7 | performance-profile | 1m 12s | ✅ PASS | All metrics normal |

**Total Duration:** 18m 42s
**Overall Status:** ✅ DEPLOYMENT SUCCESSFUL

---

## Deployment Details

### Workflows Deployed (12)
1. ✅ Linda Master Orchestrator v2.3
2. ✅ Freight Rate Request Agent v1.2
3. ✅ Dispatch Coordinator Agent v2.1
4. ✅ Trucker Selector Agent v1.5
5. ✅ Load Assignment Agent v1.3
6. ✅ Communication Manager v2.0
7. ✅ WhatsApp Handler v1.8
8. ✅ SMS Handler v1.6
9. ✅ Email Handler v1.4
10. ✅ Reply Listener Agent v1.2
11. ✅ Auto Responder Agent v1.1
12. ✅ State Machine Agent v2.0

### Backup Created
- **File:** `Backups/BACKUP_20251001_163000.tar.gz`
- **Size:** 2.3 MB
- **Files:** 127 files backed up
- **Status:** ✅ Verified and restorable

### Security Status
- ✅ 0 Critical vulnerabilities
- ✅ 0 High-risk issues
- ℹ️ 2 Low-priority recommendations
- ✅ All credentials secured
- ✅ All endpoints authenticated

### Performance Baseline
- **Avg Execution Time:** 2.3 seconds
- **Webhook Response:** 145ms avg
- **Database Queries:** 1.8s avg
- **API Calls:** 320ms avg
- **Error Rate:** 0.2% (within acceptable range)

---

## Post-Deployment Actions

### Immediate (Completed)
✅ All workflows activated
✅ Webhooks tested and responding
✅ First executions successful
✅ Monitoring alerts configured
✅ Team notified via WhatsApp

### Next 24 Hours
🔔 Monitor error rates closely
🔔 Track performance metrics
🔔 Review logs for anomalies
🔔 Gather user feedback

### Next Week
📊 Run @performance-profile after 1000 executions
📊 Generate usage analytics
📊 Update documentation if needed

---

## Notifications Sent

### Success Notifications
- ✅ WhatsApp: +1-980-266-9595 (Igor Beylin)
  - Message: "🚀 Production deployment completed successfully. All 12 workflows live and healthy."
- ✅ Supabase Log: Deployment record created
- ✅ Deployment history updated

---

## Rollback Information

### Rollback Plan (If Needed)
**Command:** `@emergency-rollback to BACKUP_20251001_163000`
**Estimated Time:** 2-3 minutes
**Backup Location:** `Backups/BACKUP_20251001_163000.tar.gz`
**Backup Verified:** ✅ Yes

---

## Risk Assessment

**Deployment Risk:** 🟢 LOW
**Reasons:**
- All validation steps passed
- Comprehensive testing completed
- Backup verified and ready
- Security audit clean
- Performance within expected range

---

## Compliance & Audit

**Change Management:** ✅ Approved
**Security Review:** ✅ Passed
**Backup Verified:** ✅ Yes
**Rollback Tested:** ✅ Ready
**Documentation Updated:** ✅ Yes

---

*Deployment completed by DEPLOY_TO_PRODUCTION pipeline v1.0.0*
*Next deployment scheduled: 2025-11-01*
```

## 🔗 Combines Well With

### Before This Pipeline
- **@workflow-diff** → **DEPLOY_TO_PRODUCTION** (review changes first)
- **@dependency-map** → **DEPLOY_TO_PRODUCTION** (understand impact)

### After This Pipeline
- **DEPLOY_TO_PRODUCTION** → **@performance-profile** (ongoing monitoring)
- **DEPLOY_TO_PRODUCTION** → **@dependency-map** (update architecture docs)

### Alternative Flows
- **DEPLOY_TO_PRODUCTION** fails → **@emergency-rollback** → fix → retry

## 💡 Pro Tips

### Tip 1: Schedule Deployments During Low Traffic
- Best time: Late evening or early morning
- Avoid: Business hours or peak times
- Have rollback plan ready

### Tip 2: Always Test in Staging First
Never deploy directly to production without staging validation.

### Tip 3: Monitor First 24 Hours Closely
Most issues surface within the first day.

### Tip 4: Communicate with Team
Notify team before, during, and after deployment.

### Tip 5: Document Everything
Keep deployment logs for audit and troubleshooting.

### Tip 6: Have Rollback Ready
Test rollback procedure before deployment.

## 🔖 Examples

### Example 1: Successful Deployment
```
User: "@deploy-production for Linda Logistics"
AI: 
  [Step 1/7] Running pre-deployment audit... ✅ PASS
  [Step 2/7] Creating safety backup... ✅ COMPLETE
  [Step 3/7] Validating 12 workflows... ✅ ALL VALID
  [Step 4/7] Checking credentials... ✅ ALL VERIFIED
  [Step 5/7] Running security audit... ✅ NO ISSUES
  [Step 6/7] Deploying to production... ✅ 12/12 DEPLOYED
  [Step 7/7] Health check... ✅ ALL SYSTEMS NORMAL
  
  🎉 DEPLOYMENT SUCCESSFUL (18m 42s)
  📊 Full report: reports/deployment_20251001.md
  📱 Team notified via WhatsApp
```

### Example 2: Deployment with Rollback
```
User: "@deploy-production for new workflows"
AI:
  [Step 1/7] Running pre-deployment audit... ✅ PASS
  [Step 2/7] Creating safety backup... ✅ COMPLETE
  [Step 3/7] Validating workflows... ❌ FAILED
  
  ⚠️ Validation Error: Workflow "New Feature" has syntax error in expression
  
  🛑 DEPLOYMENT ABORTED
  💾 Backup preserved: BACKUP_20251001_163000
  🔧 Fix required before retry
  📱 Alert sent to team
```

---

## 📚 Related Commands
- `audit-full` - Step 1 of pipeline
- `backup-versioned` - Step 2 of pipeline
- `workflow-validate` - Step 3 of pipeline
- `credentials-manage` - Step 4 of pipeline
- `security-audit` - Step 5 of pipeline
- `workflow-deploy` - Step 6 of pipeline
- `performance-profile` - Step 7 of pipeline
- `emergency-rollback` - Rollback on failure
- `workflow-diff` - Pre-deployment change review

## 📝 Version History
- **1.0.0** (2025-10-01): Initial production deployment pipeline with 7-step validation

---

*Command Standard Version: 2.0.0*
*Pipeline Type: Sequential with Automatic Rollback*
*Risk Level: HIGH - Use with caution*

