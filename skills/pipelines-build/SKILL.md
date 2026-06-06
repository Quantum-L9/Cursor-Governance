---
name: pipelines-build
description: 🔧 BUILD - Build New Feature Pipeline
disable-model-invocation: true
---

---
command: BUILD
version: 1.0.0
category: pipeline
tags: [pipeline, development, feature, build, validation]
dependencies: [workflow-validate, clean-emojis, sticky-generate, test-workflows, backup-versioned]
risk_level: safe
requires_backup: true
estimated_duration: 15-20min
---

# 🔧 BUILD - Build New Feature Pipeline

## 📖 Purpose
**Your feature development pipeline.** Complete workflow from design to ready-to-ship. Includes design, validation, documentation, testing, and backup. Use this 2-3x per week when building new features.

## 🎪 When to Use
- **New workflow creation** - Building from scratch
- **Feature development** - Adding new functionality
- **Major refactoring** - Significant changes to existing code
- **Integration work** - Connecting new systems

## 🚀 Execution - 7 Steps (15-20 min)

---

### Step 1: Design & Plan (3-5 min)
**Command:** `@think "[describe feature]"`

**Outputs:**
- Feature design document
- Implementation plan
- File structure
- Integration points
- Success criteria

**Quality Gate:**
- ✅ Clear requirements
- ✅ Implementation plan documented
- ✅ Files to modify identified
- ✅ Confidence 8+/10

---

### Step 2: Build Feature (5-8 min)
**Use:** Implementation from Step 1 plan

**Creates:**
- New workflow JSON files
- Updated configurations
- Modified code files
- Integration points

**Enterprise Standards [[memory:2510896]]:**
- ✅ Error handling comprehensive
- ✅ Supabase logging configured [[memory:2516763]]
- ✅ No hardcoded credentials [[memory:3496356]]
- ✅ Webhook architecture [[memory:2516767]]
- ✅ WhatsApp error alerts (+1-980-266-9595)

---

### Step 3: Clean & Prepare (1-2 min)
**Commands:** `@clean-emojis` + `@sticky-generate`

**Prepares workflows for n8n:**
```bash
Step 3a: @clean-emojis
  - Remove emojis from node names
  - Update connections
  - Create _CLEAN versions

Step 3b: @sticky-generate  
  - Add documentation sticky notes
  - Color-code by category [[memory:2516763]]
  - Explain complex logic
  - Document configuration
```

**Quality Gate:**
- ✅ No emojis in node names
- ✅ Documentation stickies added
- ✅ Workflows ready for import

---

### Step 4: Structural Validation (1-2 min)
**Command:** `@workflow-validate`

**Validates:**
- JSON structure correct
- All nodes properly configured
- Expressions valid
- Connections working
- No deprecated nodes
- Node versions current

**Quality Gate:**
- ✅ All workflows pass validation
- ✅ No structural errors
- ✅ No warnings

---

### Step 5: Comprehensive Testing (2-3 min)
**Command:** `@test-workflows`

**Tests:**
- Webhook endpoints
- Database connections
- API integrations
- Error handling
- End-to-end flows

**Quality Gate:**
- ✅ >95% test pass rate
- ✅ All critical paths tested
- ✅ Error handling verified

---

### Step 6: Safety Backup (1 min)
**Command:** `@backup-versioned`

**Creates:**
- Backup of current state
- Includes new feature files
- Rollback documentation
- Deployment metadata

**Quality Gate:**
- ✅ Backup created successfully
- ✅ Feature files included
- ✅ Ready for deployment

---

### Step 7: Ready for SHIP (30 sec)
**Final preparation for deployment**

```yaml
Pre-Ship Checklist:
  ✅ Feature complete
  ✅ Validated and tested
  ✅ Documented
  ✅ Backup created
  ✅ No blockers
  ✅ Ready for Pipeline: SHIP
```

**Output:** Feature ready for production deployment

---

## ✅ Success Output

```markdown
# 🔧 BUILD Pipeline - Feature Complete

**Time:** 2025-10-01 17:00:00  
**Duration:** 17m 45s  
**Feature:** Email Notifications for Buyer Matches  
**Status:** ✅ READY TO SHIP

---

## Build Summary

### Design Phase (4m 15s)
- ✅ Feature requirements documented
- ✅ Implementation plan created
- ✅ Integration points identified
- ✅ 3 workflows to modify

### Implementation Phase (7m 30s)
- ✅ Email template created
- ✅ Webhook integration configured
- ✅ Supabase logging added
- ✅ Error handling implemented
- ✅ WhatsApp alerts configured

### Preparation Phase (2m 20s)
- ✅ Emojis cleaned (0 found - already compliant)
- ✅ Documentation stickies added (8 notes)
- ✅ Workflows formatted for n8n

### Validation Phase (1m 45s)
- ✅ Structural validation: PASS
- ✅ All nodes configured correctly
- ✅ Expressions valid
- ✅ Connections working

### Testing Phase (2m 30s)
- ✅ Test Results: 18/18 passed (100%)
- ✅ Webhooks responding
- ✅ Database connections work
- ✅ Email service tested
- ✅ Error scenarios verified

### Backup Phase (55s)
- ✅ Backup created: backup_20251001_170000.tar.gz
- ✅ Feature files included
- ✅ Rollback documented

---

## Files Modified

### Created
- workflows/email_notification_buyer_match_v3.0.json
- workflows/email_notification_buyer_match_v3.0_CLEAN.json

### Modified
- buyer_matching_enhanced_v3.0.json (added email trigger)
- communication_multichannel_v3.0.json (added email node)
- environment_variables_template.env (added SMTP config)

### Documentation
- README.md updated with email feature
- Sticky notes added to 3 workflows

---

## Quality Metrics

| Category | Score | Status |
|----------|-------|--------|
| Functionality | 25/25 | ✅ Perfect |
| Enterprise Standards | 24/25 | ✅ Excellent |
| Code Quality | 23/25 | ✅ Very Good |
| Testing | 25/25 | ✅ Perfect |
| **TOTAL** | **97/100** | **✅ Excellent** |

**Confidence:** 9/10 (Very High)

---

## Next Steps

### Immediate
```bash
Pipeline: SHIP
# Deploy this feature to production
```

### Monitoring
- Watch first 10 email notifications
- Verify delivery success
- Check error logs
- Monitor performance

### Follow-Up (Optional)
- Add email open tracking
- Add click tracking
- A/B test email templates
- Add personalization

---

**Feature Status:** ✅ READY FOR PRODUCTION  
**Deployment Risk:** LOW  
**Recommended:** Deploy during next deployment window

---

*Built by BUILD Pipeline v1.0.0*
```

---

## 🔗 Combines With SHIP

### Complete Development Cycle

```bash
# Week pattern
Monday:    Pipeline: BUILD "feature A"
Tuesday:   Pipeline: SHIP (deploy feature A)
Wednesday: Pipeline: BUILD "feature B"  
Thursday:  Pipeline: SHIP (deploy feature B)
Friday:    @health-check (verify week's deployments)
```

### Rapid Development

```bash
# Morning
Pipeline: BUILD "add email notifications"
  → Feature complete in 20 min

# Afternoon  
Pipeline: SHIP
  → Deployed in 12 min

# Total: Feature live in 32 minutes ⚡
```

---

## 💡 Pro Tips

### Parallel BUILD Sessions
```bash
# Build multiple features in parallel
Terminal 1: Pipeline: BUILD "feature A"
Terminal 2: Pipeline: BUILD "feature B"
Terminal 3: Pipeline: BUILD "feature C"

# Then ship them together
Pipeline: SHIP --all
```

### Iterative Development
```bash
# Quick iteration cycle
@quick-reason "quick fix to feature"
→ Skip full BUILD
→ Go straight to SHIP

# For major changes
Pipeline: BUILD
→ Full validation
→ Pipeline: SHIP
```

### Enterprise Best Practices
- Always document in Step 1
- Never skip testing (Step 5)
- Always create backup (Step 6)
- Use @think for design phase

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial BUILD pipeline for feature development

---

*Command Standard Version: 2.0.0*
*Build It Right - Ship It Fast*

