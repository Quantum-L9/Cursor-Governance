---
name: pipelines-ship
description: 🚀 SHIP - Deploy to Production
disable-model-invocation: true
---

---
command: SHIP
version: 1.0.0
category: pipeline
tags: [pipeline, deployment, production, ship, release]
dependencies: [test-workflows, security-audit, backup-versioned, workflow-deploy, health-check]
risk_level: moderate
requires_backup: true
estimated_duration: 10-12min
---

# 🚀 SHIP - Deploy to Production

## 📖 Purpose
**Your primary deployment pipeline.** Safely ship validated features to production with comprehensive testing, security checks, and automatic rollback capability. Use this 2-5x per week when deploying new features or updates.

## 🎪 When to Use
- **Feature complete** - Ready to deploy new functionality
- **Bug fixes** - Pushing fixes to production
- **Configuration updates** - Deploying updated settings
- **Workflow improvements** - Enhanced versions ready

## ⚠️ Pre-Conditions
- ✅ Feature developed and tested locally
- ✅ Code reviewed (if team)
- ✅ No critical errors in current production
- ✅ Deployment window approved

## 🚀 Execution - 6 Steps (10-12 min)

---

### Step 1: Pre-Flight Check (30 sec)
**Quick validation before starting deployment**

```yaml
@quick-reason "verify deployment readiness"

Checks:
  ✅ Modified workflows identified
  ✅ No syntax errors
  ✅ No TODO/FIXME in code
  ✅ Documentation updated
  ✅ Ready to proceed
```

**On Failure:** Fix issues, then retry

---

### Step 2: Comprehensive Testing (2-3 min)
**Command:** `@test-workflows`

**Tests:**
- Structural validation
- Webhook endpoint testing
- Database connectivity
- Integration testing
- Error handling validation
- End-to-end flows

**Success Criteria:**
- ✅ All tests pass (>95%)
- ✅ No critical failures
- ✅ Performance acceptable

**On Failure:** Fix failing tests, restart from Step 1

---

### Step 3: Security Scan (2-3 min)
**Command:** `@security-audit`

**Scans:**
- Exposed credentials
- Hardcoded secrets
- SQL injection vectors
- Input validation
- Webhook security
- Compliance checks

**Success Criteria:**
- ✅ Zero critical issues
- ✅ Zero high priority issues
- ✅ Medium issues documented

**On Failure:** Fix security issues, restart from Step 1

---

### Step 4: Safety Backup (1 min)
**Command:** `@backup-versioned`

**Creates:**
- Timestamped backup of current production
- Backup manifest
- Rollback instructions
- Deployment metadata

**Success Criteria:**
- ✅ Backup created successfully
- ✅ Backup size >1MB
- ✅ Manifest generated

**On Failure:** Cannot proceed without backup

---

### Step 5: Deploy to n8n (1-2 min)
**Command:** `@workflow-deploy`

**Deploys:**
- Upload workflows to n8n instance
- Activate workflows
- Verify deployment
- Test webhook URLs
- Log deployment

**Success Criteria:**
- ✅ All workflows uploaded
- ✅ All workflows activated
- ✅ Webhooks responding
- ✅ Deployment logged

**On Failure:** Auto-rollback to previous version

---

### Step 6: Post-Deployment Verification (1 min)
**Command:** `@health-check`

**Verifies:**
- All services operational
- Workflows executing successfully
- No spike in errors
- Performance acceptable
- Monitoring active

**Success Criteria:**
- ✅ System health >90%
- ✅ All workflows active
- ✅ Error rate <5%
- ✅ No critical alerts

**On Failure:** Rollback and investigate

---

## ✅ Success Output

```markdown
# 🚀 SHIP Pipeline - Deployment Complete

**Time:** 2025-10-01 16:30:00  
**Duration:** 11m 23s  
**Status:** ✅ SUCCESS

---

## Deployment Summary

**Workflows Deployed:** 3
- Lead Qualification Enhanced v3.0
- Material Classification Advanced v3.0
- Buyer Matching Enhanced v3.0

**Test Results:** 48/48 passed (100%)
**Security Score:** 92/100 (Excellent)
**Backup Created:** backup_20251001_163000.tar.gz
**Deployment ID:** deploy_20251001_163000

---

## Verification Results

### Workflow Status
✅ All 3 workflows active
✅ All webhooks responding (avg 142ms)
✅ No errors in first 5 executions
✅ Performance within targets

### System Health
✅ n8n instance: HEALTHY
✅ Supabase: HEALTHY  
✅ All integrations: OPERATIONAL
✅ Error rate: 1.2% (excellent)

---

## Post-Deployment Actions

### Immediate (Next 30 min)
1. ✅ Monitor first 10-20 executions
2. ✅ Watch for error spikes
3. ✅ Check WhatsApp alerts (+1-980-266-9595)

### Short Term (Next 24 hours)
4. ✅ Review execution logs in Supabase
5. ✅ Compare performance to baseline
6. ✅ Verify all integrations stable

### Documentation
7. ✅ Update deployment log
8. ✅ Document any issues encountered
9. ✅ Share release notes with team

---

## Rollback Information

**Backup Location:** /Backup/backup_20251001_163000.tar.gz
**Rollback Command:** `@emergency-rollback --backup=backup_20251001_163000`
**Rollback Time:** ~3-5 minutes
**Data Loss:** None (Supabase logs preserved)

---

## 📊 Deployment Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Pipeline Duration | 11m 23s | <15min | ✅ |
| Tests Passed | 100% | >95% | ✅ |
| Security Score | 92/100 | >80 | ✅ |
| Deployment Success | 100% | 100% | ✅ |
| Post-Deploy Health | 98% | >90% | ✅ |

---

**Deployment:** SUCCESSFUL ✅  
**Confidence:** HIGH (all checks passed)  
**Next SHIP:** When next feature ready

---

*Deployed by SHIP Pipeline v1.0.0*
*Safe Deployment - Automatic Rollback - Peace of Mind*
```

---

## 🔗 Daily Workflow Integration

### Your Typical Ship Cycle

```bash
# Development
@think "build new feature"
→ Code and test locally

# When ready to ship
Pipeline: SHIP
  1. Pre-flight check
  2. Test workflows
  3. Security scan
  4. Backup
  5. Deploy
  6. Health check
  
# Post-deployment
@health-check  # Monitor for next hour
```

### With Your Slash Commands

```bash
/deploy → Triggers: Pipeline SHIP
  Auto-runs: all 6 steps
  Output: Deployment report
  Time: 10-12 minutes
```

---

## 💡 Pro Tips

### Pre-Ship Checklist
Before running SHIP pipeline:
- ✅ Test locally first
- ✅ Review code changes
- ✅ Update documentation
- ✅ No open TODOs
- ✅ Team notified

### Deployment Windows
**Best times to ship:**
- ✅ Early morning (low traffic)
- ✅ Mid-afternoon (before end of day)
- ❌ Avoid Friday evenings
- ❌ Avoid major holidays

### Monitoring Strategy
**First 30 min:** Active monitoring  
**Next 2 hours:** Periodic checks  
**Next 24 hours:** Review logs  
**Next week:** Performance comparison

---

## 🚨 Auto-Rollback Conditions

Pipeline auto-rolls back if:
- ❌ Tests fail during Step 2
- ❌ Critical security issue in Step 3
- ❌ Deployment fails in Step 5
- ❌ Health check fails in Step 6
- ❌ Error rate >20% in first 5 min

Manual rollback available anytime:
```bash
@emergency-rollback --deployment=latest
```

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial SHIP pipeline - streamlined deployment

---

*Command Standard Version: 2.0.0*
*Ship Fast - Ship Safe - Ship Often*

