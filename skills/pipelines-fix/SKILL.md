---
name: pipelines-fix
description: 🚨 FIX - Emergency Recovery Pipeline
disable-model-invocation: true
---

---
command: FIX
version: 1.0.0
category: pipeline
tags: [pipeline, emergency, fix, recovery, incident]
dependencies: [emergency-rollback, health-check, test-workflows, workflow-deploy]
risk_level: moderate
requires_backup: true
estimated_duration: 3-5min
---

# 🚨 FIX - Emergency Recovery Pipeline

## 📖 Purpose
**Your emergency response pipeline.** Fast incident response for production issues. Includes rollback, investigation, fix, redeploy, and verification. Use when things break in production.

## 🎪 When to Use
- **Production down** - Critical system failure
- **Workflows failing** - High error rates
- **Bad deployment** - Need to rollback recent deploy
- **Data issues** - Corrupted data or state
- **Integration failures** - External service problems

## ⚠️ When NOT to Use
- Planned maintenance (use Pipeline: CHECK)
- Feature development (use Pipeline: BUILD)
- Normal deployments (use Pipeline: SHIP)

## 🚀 Execution - 5 Fast Steps (3-5 min)

---

### Step 1: Assess Situation (30 sec)
**Quick diagnostic to understand the problem**

```yaml
@health-check --quick

Questions:
  - What's broken?
  - How bad is it?
  - When did it start?
  - What changed recently?
  - Is rollback needed?
```

**Decision Point:**
- **If recent deployment caused issue** → Proceed to Step 2 (Rollback)
- **If pre-existing issue** → Skip to Step 3 (Investigate & Fix)

---

### Step 2: Emergency Rollback (1-2 min) [IF NEEDED]
**Command:** `@emergency-rollback --backup=latest`

**Rollback Actions:**
- Restore previous working version
- Deactivate broken workflows
- Reactivate stable workflows
- Verify restoration
- Log incident

**Success Criteria:**
- ✅ Previous version restored
- ✅ System functional again
- ✅ Error rate normalized
- ✅ Users can operate

**On Success:** System stabilized, proceed to Step 3 to fix root cause

---

### Step 3: Investigate & Fix (1-2 min)
**Command:** `@think "investigate [specific issue]"`

**Investigation:**
- Review error logs (Supabase)
- Check workflow executions
- Identify root cause
- Design fix
- Implement solution

**Enterprise Standards [[memory:2510896]]:**
- ✅ Fix includes error handling
- ✅ Supabase logging added [[memory:2516763]]
- ✅ No quick hacks (proper fix)
- ✅ Tests included

**Output:** Root cause identified and fixed

---

### Step 4: Test Fix (1 min)
**Command:** `@test-workflows --targeted`

**Tests:**
- Fixed workflow(s)
- Integration points
- Error scenarios
- Regression check

**Success Criteria:**
- ✅ Fix resolves issue
- ✅ No new errors introduced
- ✅ Tests pass (>95%)

**On Failure:** Return to Step 3, refine fix

---

### Step 5: Redeploy & Verify (1 min)
**Commands:** `@workflow-deploy` + `@health-check`

**Redeploy:**
- Deploy fixed workflows
- Activate workflows
- Verify deployment

**Verify:**
- System operational
- Error rate normal
- Performance acceptable
- Issue resolved

**Success Criteria:**
- ✅ Deployment successful
- ✅ System healthy
- ✅ Issue not recurring
- ✅ Monitoring confirms fix

---

## ✅ FIX Report Output

```markdown
# 🚨 FIX Pipeline - Incident Resolution

**Time:** 2025-10-02 14:23:00  
**Duration:** 4m 37s  
**Incident:** Material classification workflow failing  
**Status:** ✅ RESOLVED

---

## Incident Summary

**Reported:** 2025-10-02 14:18:00  
**Severity:** 🔴 HIGH (workflow 100% failure rate)  
**Impact:** Material classification unavailable (15 failed requests)  
**Downtime:** 5 minutes  
**Resolution Time:** 4m 37s

---

## Timeline

### 14:18 - Incident Detected
- WhatsApp alert received (+1-980-266-9595)
- Error: "OpenAI API key invalid"
- Workflow: material_classification_advanced_v3.0

### 14:19 - Assessment (Step 1)
- Ran @health-check
- Identified: API key rotation broke integration
- Decision: No rollback needed (simple fix)

### 14:20 - Skipped Rollback (Step 2)
- Issue isolated to one workflow
- Other workflows operational
- Fix faster than rollback

### 14:20 - Investigation & Fix (Step 3)
- Root cause: Environment variable not updated after key rotation
- Fix: Update OPENAI_API_KEY in n8n
- Updated workflow configuration
- Added validation step

### 14:22 - Testing (Step 4)
- Test workflow with new key: ✅ SUCCESS
- Test classification: ✅ WORKING
- Test error handling: ✅ PROPER
- Regression tests: ✅ ALL PASS

### 14:23 - Redeploy & Verify (Step 5)
- Redeployed workflow: ✅ SUCCESS
- Health check: ✅ ALL SYSTEMS OPERATIONAL
- Error rate normalized: ✅ 0% failure
- Monitoring: ✅ No recurring issues

---

## Root Cause Analysis

**Problem:** OpenAI API key rotated but environment variable not updated in n8n

**Why it happened:**
- Key rotation process incomplete
- n8n environment variable not in rotation checklist
- No validation after rotation

**Why it wasn't caught:**
- No pre-deployment credential validation
- Staging environment using different key
- Test suite doesn't catch env var issues

**Contributing factors:**
- Manual credential rotation process
- No automated validation
- Documentation gap

---

## Fix Implemented

### Immediate Fix
```yaml
What: Updated OPENAI_API_KEY in n8n environment
How: Settings → Environment Variables → Update value
Verification: Test classification request → SUCCESS
```

### Permanent Fix
```yaml
What: Added credential validation to deployment pipeline
How: Modified Pipeline: SHIP to include @credentials-manage
Documentation: Updated deployment checklist
Prevention: Won't happen again
```

### Process Improvement
```yaml
What: Created credential rotation checklist
Items:
  - Update .env file
  - Update n8n environment variables
  - Update Supabase secrets
  - Test all integrations
  - Verify no failures
```

---

## Prevention Measures

### Immediate (Today)
1. ✅ Update deployment checklist
2. ✅ Add credential validation step
3. ✅ Document rotation process

### Short Term (This Week)
4. ✅ Add pre-deployment credential check
5. ✅ Create automated rotation script
6. ✅ Set up credential expiry alerts

### Long Term (This Month)
7. ✅ Implement secret management system
8. ✅ Automate credential rotation
9. ✅ Add integration tests for credentials

---

## Post-Incident Metrics

### Recovery Performance
- **Detection Time:** <1 minute (WhatsApp alert)
- **Response Time:** <1 minute (started FIX pipeline)
- **Resolution Time:** 4m 37s
- **Total Downtime:** 5 minutes
- **Mean Time to Recovery (MTTR):** 4m 37s ✅ Excellent

### Impact Assessment
- **Failed Requests:** 15
- **Users Affected:** Minimal (internal testing)
- **Revenue Impact:** $0 (no customer-facing impact)
- **Data Loss:** None (Supabase logs preserved)
- **Reputational Impact:** None (caught early)

---

## Lessons Learned

### What Went Well ✅
- WhatsApp alerts worked perfectly
- FIX pipeline executed smoothly
- Fast resolution (under 5 minutes)
- No data loss
- Clear rollback capability available

### What Could Improve ⚠️
- Credential rotation checklist incomplete
- No automated credential validation
- Staging didn't catch issue (different keys)
- Documentation gap in rotation process

### Action Items
1. ✅ Update deployment pipeline (DONE)
2. ✅ Create rotation checklist (DONE)
3. ⏳ Build credential validation automation
4. ⏳ Improve staging environment parity

---

## Next Steps

### Immediate (Next Hour)
```bash
@health-check           # Verify stability
@test-workflows         # Confirm no regressions
# Monitor for 1 hour
```

### Follow-Up (This Week)
```bash
@think "build credential validation automation"
@think "improve staging environment"
```

### Documentation
```bash
@quick-reason "update incident log"
@quick-reason "document lessons learned"
```

---

**Incident:** RESOLVED ✅  
**System Status:** OPERATIONAL  
**Confidence:** HIGH (issue fixed, prevention added)  
**Next CHECK:** Sunday as scheduled

---

*Fixed by FIX Pipeline v1.0.0 in 4m 37s*
*Fast Response - Clean Resolution - Better Process*
```

---

## 🎯 FIX Pipeline Decision Tree

```yaml
Production Issue Detected:

  Is it a recent deployment?
    YES → Step 2: Rollback first
    NO → Skip to Step 3: Investigate
    
  After rollback (if performed):
    System stable now?
      YES → Step 3: Fix root cause
      NO → Escalate to team, @deep-reason
      
  After fix implemented:
    Tests pass?
      YES → Step 5: Redeploy
      NO → Refine fix, retry Step 4
      
  After redeployment:
    Health check pass?
      YES → Incident resolved ✅
      NO → Rollback again, deeper investigation
```

---

## 🚨 Incident Severity Levels

```yaml
🔴 CRITICAL (Use FIX immediately):
  - Complete system down
  - Data corruption
  - Security breach
  - All workflows failing
  - Customer-facing impact
  
🟡 HIGH (Use FIX within 1 hour):
  - Key workflow failing
  - High error rates (>20%)
  - Integration down
  - Performance severely degraded
  
🟠 MEDIUM (Use FIX within 4 hours):
  - Single workflow issues
  - Moderate error rates (10-20%)
  - Slow performance
  - Non-critical integration issues
  
🟢 LOW (Use regular fix process):
  - Minor bugs
  - Low error rates (<10%)
  - Documentation issues
  - Cosmetic problems
```

---

## 💡 Pro Tips

### Fast Response
- Keep WhatsApp notifications on (+1-980-266-9595)
- Know your rollback command by heart
- Have n8n dashboard bookmarked
- Keep Supabase logs accessible

### During Incident
- Stay calm, follow the pipeline
- Document everything
- Communicate status to team
- Don't skip testing (Step 4)

### After Incident
- Always do post-mortem
- Update prevention measures
- Document lessons learned
- Improve monitoring

### Common Scenarios

**API Key Issues:**
```bash
FIX Steps 1,3,4,5 (skip rollback)
Time: 3-4 minutes
```

**Bad Deployment:**
```bash
FIX Steps 1,2,5 (rollback → redeploy)
Time: 2-3 minutes
```

**Complex Bug:**
```bash
FIX Steps 1,2,3,4,5 (full pipeline)
Time: 5-8 minutes
```

---

## 🔗 Combines Well With

### Emergency Response
```bash
Alert received → Pipeline: FIX
  → System restored
  → Post-mortem documentation
  → Prevention measures added
```

### After FIX
```bash
Pipeline: FIX (resolve incident)
→ @quick-reason "document incident"
→ @think "implement prevention"
→ Pipeline: CHECK (verify system health)
```

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial FIX pipeline for emergency response

---

*Command Standard Version: 2.0.0*
*Fast Recovery - Zero Panic - Continuous Improvement*

