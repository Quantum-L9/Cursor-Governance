---
name: pipelines-_legacy-new-workflow-setup
description: ✨ New Workflow Setup Pipeline
disable-model-invocation: true
---

---
command: NEW_WORKFLOW_SETUP
version: 1.0.0
category: pipeline
tags: [pipeline, setup, validation, new-workflow, onboarding]
dependencies: [workflow-validate, dependency-map, security-audit, sticky-generate, credentials-manage, backup-versioned]
risk_level: moderate
requires_backup: true
estimated_duration: 5-10min
---

# ✨ New Workflow Setup Pipeline

## 📖 Purpose
Complete setup and validation pipeline for new workflows before integration into the production system. Ensures new workflows meet quality standards, security requirements, and integrate cleanly with existing architecture.

## 🎪 When to Use
- Adding new workflow to system
- Integrating third-party workflows
- After major workflow refactor
- Before first deployment of new feature
- Onboarding workflow from another environment

## ⚠️ When NOT to Use
- Updating existing workflows (use @workflow-validate)
- Minor tweaks or fixes (overkill)
- Already validated workflows

## 🔍 Pre-Conditions
- [ ] New workflow JSON file exists
- [ ] Workflow purpose and requirements documented
- [ ] Required credentials identified
- [ ] Integration points known

## 🚀 Execution

This pipeline executes **6 validation and setup steps**:

---

### 📋 Pipeline Overview
```
Step 1: Structural Validation
Step 2: Dependency Analysis
Step 3: Security Scan
Step 4: Documentation Generation
Step 5: Credentials Verification
Step 6: Pre-Integration Backup
```

---

### Step 1: Structural Validation (1-2 min)
**Command:** `@workflow-validate` (focused on new workflow)

**Purpose:** Ensure workflow is technically sound and ready

**Validates:**
- ✅ JSON structure is valid
- ✅ All nodes are properly configured
- ✅ Expressions have correct syntax
- ✅ Connections are valid
- ✅ No missing parameters
- ✅ Node versions are current (not deprecated)

**Common Issues Caught:**
- Malformed JSON
- Missing node parameters
- Invalid expressions
- Broken connections
- Deprecated nodes

**Success Criteria:**
- ✅ Workflow passes all structural checks
- ✅ No syntax errors
- ✅ All nodes properly configured
- ✅ Ready for integration

**Output:**
```
✅ Structural Validation Complete
Workflow: "Email Automation Handler"
Nodes: 8 (all valid)
Connections: 12 (all valid)
Expressions: 15 (all syntactically correct)
Status: READY FOR INTEGRATION
```

---

### Step 2: Dependency Analysis (2-3 min)
**Command:** `@dependency-map` (focused on new workflow)

**Purpose:** Understand how new workflow fits into existing architecture

**Analyzes:**
- **Incoming Dependencies:** What will call this workflow?
- **Outgoing Dependencies:** What does this workflow call?
- **Data Flow:** What data goes in/out?
- **External Services:** What APIs does it use?
- **Potential Conflicts:** Does it overlap with existing workflows?

**Checks:**
- Will this create circular dependencies?
- Does it conflict with existing webhooks?
- Are all called services available?
- Is it a duplicate of existing functionality?

**Success Criteria:**
- ✅ Dependencies identified and documented
- ✅ No circular dependencies created
- ✅ No webhook path conflicts
- ✅ Integration points clear

**Output:**
```
📊 Dependency Analysis
Workflow: "Email Automation Handler"

Incoming (Called By):
- Communication Manager → /webhook/email-automation

Outgoing (Calls To):
- SendGrid API (email sending)
- Supabase (logging)

Data Flow:
- Input: email_address, subject, body, template_id
- Output: email_sent (boolean), message_id

External Services:
- SendGrid API (requires: sendgrid_api_key)
- Supabase API (requires: supabase_api_key)

Integration Risk: LOW
- No conflicts detected
- Clean integration path
- No circular dependencies
```

---

### Step 3: Security Scan (1-2 min)
**Command:** `@security-audit` (focused on new workflow)

**Purpose:** Ensure new workflow doesn't introduce security vulnerabilities

**Scans For:**
- 🔴 Exposed credentials or API keys
- 🔴 Hardcoded secrets
- 🟡 Unsecured webhook endpoints
- 🟡 Missing input validation
- 🟡 SQL injection risks
- 🟢 Best practice violations

**Security Checks:**
- Are credentials properly referenced (not hardcoded)?
- Are webhook endpoints secured?
- Is input data validated?
- Are errors handled securely?
- Is sensitive data logged?

**Success Criteria:**
- ✅ Zero critical security issues
- ✅ No exposed credentials
- ✅ Input validation present
- ✅ Secure error handling

**Output:**
```
🔒 Security Scan Complete
Workflow: "Email Automation Handler"

Critical Issues: 0
High Priority: 0
Medium Priority: 1
Low Priority: 2

⚠️ Medium Priority:
- Webhook endpoint should add authentication header check

📋 Low Priority:
- Consider rate limiting for email sends
- Add logging for failed authentication attempts

Overall Security: GOOD (can integrate with medium-priority fix)
```

---

### Step 4: Documentation Generation (1-2 min)
**Command:** `@sticky-generate`

**Purpose:** Generate comprehensive sticky notes for workflow documentation

**Generates:**
- **Overview Sticky:** Workflow purpose and functionality
- **Setup Instructions:** How to configure and use
- **Node Documentation:** Purpose of each node
- **Webhook Documentation:** Endpoints and payloads
- **Error Handling:** How errors are managed
- **Dependencies:** What it requires/provides

**Sticky Note Sections:**
```markdown
## Workflow Overview
Purpose, trigger type, expected inputs/outputs

## Setup Instructions
1. Configure credentials
2. Set webhook URL
3. Test with sample data

## Node Breakdown
- Node 1: Purpose and configuration
- Node 2: Purpose and configuration
[...]

## Webhook Documentation
Endpoint: /webhook/email-automation
Method: POST
Payload: { email_address, subject, body }

## Error Handling
- SendGrid failure → retry 3x → log error → notify admin
- Invalid input → return 400 → log warning

## Dependencies
Requires: sendgrid_api_key, supabase_api_key
Calls: SendGrid API, Supabase logging
Called by: Communication Manager
```

**Success Criteria:**
- ✅ All sticky notes generated
- ✅ Comprehensive documentation
- ✅ Setup instructions clear
- ✅ Enterprise-grade quality

**Output:**
```
📝 Documentation Generated
Workflow: "Email Automation Handler"

Sticky Notes Created:
✅ Overview & Purpose (bright blue)
✅ Setup Instructions (yellow)
✅ Webhook Documentation (green)
✅ Error Handling (orange)
✅ Dependencies (purple)

Total Stickies: 5
Documentation Coverage: 100%
Ready for team onboarding
```

---

### Step 5: Credentials Verification (30-60 sec)
**Command:** `@credentials-manage`

**Purpose:** Verify all required credentials exist and are valid

**Checks:**
- All credential references in workflow
- Credentials exist in target environment
- Credentials have proper permissions
- No placeholder credentials

**For New Workflow:**
- Lists required credentials
- Checks if they exist
- Validates they're production-ready
- Flags missing credentials

**Success Criteria:**
- ✅ All required credentials identified
- ✅ All credentials exist in environment
- ✅ No placeholders or test credentials
- ✅ Proper permissions verified

**Output:**
```
🔑 Credentials Verification
Workflow: "Email Automation Handler"

Required Credentials:
✅ sendgrid_api_key (exists, valid permissions)
✅ supabase_api_key (exists, valid permissions)

Status: ALL CREDENTIALS READY
No action needed - ready to deploy
```

---

### Step 6: Pre-Integration Backup (30 sec)
**Command:** `@backup-versioned --pre-integration`

**Purpose:** Safety backup before adding new workflow to system

**Creates:**
- Backup of current system state
- Timestamp: `BACKUP_PREINTEGRATION_YYYYMMDD_HHMMSS`
- Allows easy rollback if integration causes issues

**Success Criteria:**
- ✅ Backup created successfully
- ✅ Current state preserved
- ✅ Rollback path available

**Output:**
```
💾 Pre-Integration Backup Created
File: BACKUP_PREINTEGRATION_20251001_143000.tar.gz
Size: 2.2 MB
Status: VERIFIED

Rollback command if needed:
@emergency-rollback to BACKUP_PREINTEGRATION_20251001_143000
```

---

## ✅ Post-Conditions
- [ ] Workflow validated and ready
- [ ] Dependencies mapped
- [ ] Security verified
- [ ] Documentation complete
- [ ] Credentials confirmed
- [ ] Backup created
- [ ] **Ready for integration!**

## 🔗 Success Metrics
1. **Validation:** Workflow passes all technical checks
2. **Security:** Zero critical vulnerabilities
3. **Documentation:** 100% coverage with sticky notes
4. **Integration Ready:** Clear path to production
5. **Rollback Ready:** Backup available

## 📊 Output Format

### New Workflow Setup Report
```markdown
# ✨ New Workflow Setup Report
**Workflow:** Email Automation Handler
**Date:** 2025-10-01 14:30:00
**Duration:** 7 minutes 28 seconds
**Status:** ✅ READY FOR INTEGRATION

---

## Workflow Summary
**Name:** Email Automation Handler
**Purpose:** Automated email sending via SendGrid
**Type:** Webhook-triggered
**Nodes:** 8
**Complexity:** Medium (5/10)

---

## Validation Results

| Step | Check | Duration | Status | Notes |
|------|-------|----------|--------|-------|
| 1 | Structural Validation | 1m 32s | ✅ PASS | All nodes valid |
| 2 | Dependency Analysis | 2m 15s | ✅ PASS | Clean integration |
| 3 | Security Scan | 1m 48s | ⚠️ PASS | 1 medium-priority item |
| 4 | Documentation | 1m 22s | ✅ PASS | 100% coverage |
| 5 | Credentials | 41s | ✅ PASS | All ready |
| 6 | Backup | 30s | ✅ PASS | Rollback ready |

**Overall:** ✅ READY FOR INTEGRATION

---

## Integration Details

### Webhook Endpoint
**URL:** `https://ibeylin.app.n8n.cloud/webhook/email-automation`
**Method:** POST
**Auth:** Bearer token required

### Required Credentials
✅ sendgrid_api_key (configured)
✅ supabase_api_key (configured)

### Dependencies
**Called By:** Communication Manager
**Calls To:** SendGrid API, Supabase

### Data Flow
**Input:** `{ email_address, subject, body, template_id }`
**Output:** `{ email_sent: boolean, message_id: string }`

---

## Action Items Before Deployment

### Critical (Must Fix)
- None

### Recommended (Should Fix)
- [ ] Add authentication header check to webhook endpoint

### Optional (Nice to Have)
- [ ] Add rate limiting for email sends
- [ ] Add logging for failed authentication attempts

---

## Next Steps

1. ✅ Review this setup report
2. ⚠️ Address recommended security item (webhook auth)
3. ✅ Test workflow with sample data in staging
4. ✅ When ready, deploy with `@deploy-production`

---

## Rollback Plan
If integration causes issues:
```
@emergency-rollback to BACKUP_PREINTEGRATION_20251001_143000
```

---

*Setup completed by NEW_WORKFLOW_SETUP pipeline v1.0.0*
*Workflow ready for staging testing*
```

## 🔗 Combines Well With

### Before This Pipeline
- Build workflow → **NEW_WORKFLOW_SETUP**

### After This Pipeline
- **NEW_WORKFLOW_SETUP** → Test in staging → **@deploy-production**

## 💡 Pro Tips

### Tip 1: Always Run This for New Workflows
Don't skip validation - catch issues early.

### Tip 2: Review Dependency Analysis Carefully
Understanding integration points prevents issues.

### Tip 3: Address Security Items Before Production
Even "medium priority" items should be fixed.

### Tip 4: Test in Staging First
After setup, always test before production.

### Tip 5: Keep Documentation Updated
Generated stickies should evolve with workflow.

## 🔖 Examples

### Example 1: Clean Setup
```
User: "@new-workflow-setup for Email_Automation_Handler.json"
AI:
  ✨ Setting up new workflow...
  
  [1/6] Structural validation... ✅ PASS (1m 32s)
  [2/6] Dependency analysis... ✅ PASS (2m 15s)
  [3/6] Security scan... ✅ PASS (1m 48s)
  [4/6] Documentation... ✅ COMPLETE (1m 22s)
  [5/6] Credentials check... ✅ ALL READY (41s)
  [6/6] Pre-integration backup... ✅ CREATED (30s)
  
  ✅ SETUP COMPLETE (7m 28s)
  📊 Status: READY FOR INTEGRATION
  📋 Next: Test in staging, then deploy
```

### Example 2: Setup with Issues
```
User: "@new-workflow-setup for New_Feature.json"
AI:
  [1/6] Structural validation... ❌ FAILED
  
  Issues found:
  - Node "HTTP Request" missing URL parameter
  - Expression syntax error in "Set" node line 3
  - Deprecated node detected: "Function" (use Code node)
  
  ⚠️ SETUP PAUSED
  Fix these issues and run setup again
```

---

## 📚 Related Commands
- `workflow-validate` - Structural validation
- `dependency-map` - Dependency analysis
- `security-audit` - Security scanning
- `sticky-generate` - Documentation generation
- `credentials-manage` - Credential verification
- `backup-versioned` - Pre-integration backup
- `deploy-production` - Next step after setup

## 📝 Version History
- **1.0.0** (2025-10-01): Initial new workflow setup pipeline with 6-step validation

---

*Command Standard Version: 2.0.0*
*Pipeline Type: Validation & Onboarding*
*Best Practice: Run for EVERY new workflow*

