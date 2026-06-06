---
name: n8n-workflow-diff
description: 🔍 N8N Workflow Diff Engine
disable-model-invocation: true
---

---
command: WORKFLOW_DIFF
version: 1.0.0
category: n8n
tags: [comparison, version-control, quality-assurance, n8n, diff]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: 1-3min
---

# 🔍 N8N Workflow Diff Engine

## 📖 Purpose
Compare two versions of an n8n workflow and generate a detailed diff report showing all changes in nodes, connections, credentials, expressions, and sticky notes.

## 🎪 When to Use
- Before deploying workflow changes to production
- Reviewing changes made by team members
- Understanding what changed between versions
- Auditing workflow modifications
- Troubleshooting broken workflows after updates

## ⚠️ When NOT to Use
- Comparing completely different workflows (not versions of same workflow)
- When you need to merge workflows (different use case)

## 🔍 Pre-Conditions
- [ ] Two workflow JSON files exist (or git commits with workflows)
- [ ] Workflows are valid n8n JSON format
- [ ] Both versions are for the same workflow (same base)

## 🚀 Execution

### Step 1: Identify Workflow Versions
Specify which two versions to compare:
- Option A: Two different files (`workflow-v1.json` vs `workflow-v2.json`)
- Option B: Git commits (`main` vs `feature-branch`)
- Option C: Current vs. backup (`workflow.json` vs `backups/BACKUP_20250101/workflow.json`)

### Step 2: Parse JSON Structure
Load and parse both workflow JSON files:
```javascript
const workflow1 = JSON.parse(file1);
const workflow2 = JSON.parse(file2);
```

### Step 3: Compare All Components

#### A. Node Changes
- **Added Nodes:** Nodes in v2 not in v1
- **Removed Nodes:** Nodes in v1 not in v2
- **Modified Nodes:** Same node ID but different parameters

#### B. Connection Changes
- **New Connections:** Edges added
- **Removed Connections:** Edges deleted
- **Modified Connections:** Connection type/conditions changed

#### C. Parameter Changes
For each modified node, compare:
- Node parameters
- Expressions (`{{ }}` code)
- Settings and options
- Retry policies
- Timeout values

#### D. Credential Changes
- Credential reference changes
- New credential requirements
- Removed credential usage

#### E. Metadata Changes
- Workflow name/description
- Tags
- Sticky notes
- Positioning

### Step 4: Risk Assessment
For each change, assign risk level:
- 🟢 **Low Risk:** Cosmetic (position, notes, names)
- 🟡 **Medium Risk:** Parameter tweaks, new optional nodes
- 🔴 **High Risk:** Logic changes, removed nodes, credential changes, expression modifications

### Step 5: Generate Diff Report
Output comprehensive markdown report (see Output Format section).

## ✅ Post-Conditions
- [ ] Diff report generated successfully
- [ ] All changes categorized by type
- [ ] Risk assessment completed
- [ ] Testing recommendations provided

## 🔗 Success Metrics
1. **Completeness:** All changes detected and categorized
2. **Clarity:** Report is easy to understand for non-technical reviewers
3. **Actionability:** Clear recommendations for testing and validation

## 🚨 Error Handling

### Common Errors
1. **Invalid JSON**
   - Cause: Malformed workflow file
   - Solution: Validate JSON syntax first
   - Prevention: Use @workflow-validate before diff

2. **Missing Files**
   - Cause: File path incorrect
   - Solution: Verify file paths exist
   - Prevention: Use file picker or autocomplete

3. **Completely Different Workflows**
   - Cause: Comparing unrelated workflows
   - Solution: Verify workflow IDs/names match
   - Prevention: Check workflow metadata first

## 📊 Output Format

### Diff Report Structure
```markdown
# Workflow Diff Report
**Workflow:** [Workflow Name]
**Comparison:** v1.2.0 → v1.3.0
**Generated:** 2025-10-01 14:30:52

## 📊 Summary
- 3 nodes added
- 1 node removed
- 5 nodes modified
- 2 new connections
- 0 connections removed
- **Overall Risk:** 🟡 MEDIUM

---

## ➕ Added Nodes

### 1. HTTP Request - Fetch Customer Data
- **Type:** n8n-nodes-base.httpRequest
- **Position:** After "Webhook Trigger"
- **Risk:** 🟡 Medium (new external API call)
- **Testing:** Verify API credentials and response handling

### 2. Set Node - Format Response
- **Type:** n8n-nodes-base.set
- **Position:** After "HTTP Request"
- **Risk:** 🟢 Low (data transformation only)

---

## ➖ Removed Nodes

### 1. Function Node - Old Logic
- **Type:** n8n-nodes-base.function
- **Reason:** Likely replaced by new HTTP Request node
- **Risk:** 🔴 High (logic removal)
- **Action Required:** Verify replacement logic is equivalent

---

## 🔄 Modified Nodes

### 1. Supabase Insert
**Changes:**
- Parameter `table` changed: `"orders"` → `"customer_orders"`
- Added parameter: `returnFields: "*"`
- Expression updated in `data` field

**Risk:** 🔴 High (database table change)
**Testing:** 
- Verify new table exists in Supabase
- Confirm table schema matches data
- Test with sample data

### 2. WhatsApp Send Message
**Changes:**
- Parameter `to` expression modified
- Removed parameter: `template_id`
- Now using freeform message instead of template

**Risk:** 🟡 Medium (message format change)
**Testing:**
- Verify message formatting
- Test with various phone number formats

---

## 🔗 Connection Changes

### New Connections
1. Webhook → HTTP Request → Set Node → Supabase
2. Error Handler → Notification Node

### Removed Connections
None

---

## 🔐 Credential Changes

### Modified
- `supabaseApi` now used by 2 additional nodes
- Ensure credential has sufficient permissions

---

## 📝 Sticky Note Changes
- Added documentation for new HTTP Request section
- Updated error handling notes

---

## ⚠️ Testing Recommendations

### Critical Tests (Must Do)
1. Test removed "Function Node" logic is preserved
2. Verify Supabase table name change (`orders` → `customer_orders`)
3. Test new HTTP Request API endpoint
4. Validate WhatsApp message formatting

### Important Tests (Should Do)
1. Test error handling paths
2. Verify all expressions still resolve correctly
3. Check credential permissions
4. Test with edge cases

### Optional Tests
1. Verify cosmetic changes (sticky notes, positions)
2. Performance comparison between versions

---

## 🎯 Deployment Recommendation
**Status:** ⚠️ PROCEED WITH CAUTION
**Reason:** High-risk database table name change detected

**Action Plan:**
1. Run @workflow-validate on new version
2. Test in staging environment first
3. Backup production database before deploy
4. Have rollback plan ready (@emergency-rollback)
5. Monitor closely for first 24 hours

---

*Diff generated by WORKFLOW_DIFF v1.0.0*
```

## 🔗 Combines Well With

### Before This Command
- **@backup-versioned** → **WORKFLOW_DIFF** (compare with backup)
- **git diff** → **WORKFLOW_DIFF** (compare git versions)

### After This Command
- **WORKFLOW_DIFF** → **@workflow-validate** (validate new version)
- **WORKFLOW_DIFF** → **@deploy-production** (if diff looks good)
- **WORKFLOW_DIFF** → **@emergency-rollback** (if issues found)

### Common Pipelines
1. **Pre-Deploy Review:** backup → WORKFLOW_DIFF → validate → deploy
2. **Troubleshooting:** WORKFLOW_DIFF → identify-issue → rollback
3. **Code Review:** git-checkout → WORKFLOW_DIFF → approve/reject

## 💡 Pro Tips
- Run diff before EVERY production deployment
- Save diff reports for audit trail
- Use in pull request reviews
- Compare against last known good backup when debugging
- Color-code risk levels for quick scanning
- Include specific testing recommendations

## 🔖 Examples

### Example 1: Compare Two Files
```
Input:
  File 1: Sub_Agents/02_Dispatch_Management/04_Dispatch_Coordinator_Agent_v1.0.json
  File 2: Sub_Agents/02_Dispatch_Management/04_Dispatch_Coordinator_Agent_v1.1.json

Output: [Full diff report as shown above]
```

### Example 2: Compare Git Versions
```
Input:
  Version 1: git:main:workflow.json
  Version 2: git:feature-update:workflow.json

Output: Diff report highlighting branch differences
```

### Example 3: Compare with Backup
```
Input:
  Current: Master_Agent/02_Linda_Master_Orchestrator.json
  Backup: Backups/BACKUP_20250930/02_Linda_Master_Orchestrator.json

Output: Shows all changes since backup was created
```

---

## 📚 Related Commands
- `workflow-validate` - Validate workflows before/after comparison
- `backup-versioned` - Create backup before making changes
- `emergency-rollback` - Revert if diff reveals problems
- `deploy-production` - Deploy after successful diff review

## 📝 Version History
- **1.0.0** (2025-10-01): Initial workflow diff engine with comprehensive change detection

---

*Command Standard Version: 2.0.0*

