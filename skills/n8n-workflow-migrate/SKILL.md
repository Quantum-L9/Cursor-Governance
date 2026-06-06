---
name: n8n-workflow-migrate
description: 🚀 N8N Workflow Migration
disable-model-invocation: true
---

---
command: WORKFLOW_MIGRATE
version: 1.0.0
category: n8n
tags: [migration, environment, deployment, production, staging]
dependencies: [workflow-validate, backup-versioned]
risk_level: high
requires_backup: true
estimated_duration: 5-10min
---

# 🚀 N8N Workflow Migration

## 📖 Purpose
Safely migrate n8n workflows between environments (dev → staging → production) with automatic credential remapping, URL updates, and environment-specific configuration adjustments.

## 🎪 When to Use
- Promoting workflows from dev to staging
- Deploying tested workflows to production
- Creating environment-specific variants
- Setting up new environments with existing workflows

## ⚠️ When NOT to Use
- Simple file copying (use regular deployment)
- Same environment updates (use regular deploy)
- Experimental/untested workflows (test in dev first)

## 🔍 Pre-Conditions
- [ ] Workflow validated in source environment
- [ ] Target environment credentials configured
- [ ] Backup of target environment created
- [ ] Environment mapping configuration exists
- [ ] All required nodes available in target environment

## 🚀 Execution

### Step 1: Validate Source Workflow
Run validation on source workflow:
- Check JSON structure
- Verify all nodes are standard (no custom nodes unless available in target)
- Confirm no hardcoded environment-specific values

### Step 2: Create Environment Mapping
Define mappings for environment-specific values:

```yaml
environment_mapping:
  credentials:
    dev_supabase_api: prod_supabase_api
    dev_twilio: prod_twilio
    dev_openai: prod_openai
  
  urls:
    webhook_base: 
      dev: "https://ibeylin-dev.app.n8n.cloud"
      prod: "https://ibeylin.app.n8n.cloud"
    
  variables:
    database_name:
      dev: "dev_database"
      prod: "production_database"
    
    notification_phone:
      dev: "+1-555-TEST-001"
      prod: "+1-980-266-9595"
```

### Step 3: Transform Workflow
Apply transformations:

#### A. Credential Remapping
```javascript
// Replace credential IDs
workflow.nodes.forEach(node => {
  if (node.credentials) {
    Object.keys(node.credentials).forEach(credType => {
      const devCred = node.credentials[credType].id;
      node.credentials[credType].id = credentialMap[devCred];
    });
  }
});
```

#### B. URL Updates
Replace environment-specific URLs in:
- Webhook nodes
- HTTP Request nodes  
- Expressions containing URLs

#### C. Variable Substitution
Update environment variables in:
- Node parameters
- Expressions
- Sticky notes (documentation)

### Step 4: Validation Checks
Run comprehensive validation:
- [ ] All credentials exist in target environment
- [ ] All webhook URLs are correct
- [ ] No dev-specific values remain
- [ ] Expressions are valid
- [ ] No syntax errors

### Step 5: Backup Target Environment
Create backup before migration:
```bash
PIPELINE_EXECUTE backup-versioned --environment=production
```

### Step 6: Deploy to Target
- Upload workflow to target environment
- Activate workflow
- Test trigger endpoints
- Verify first execution

### Step 7: Post-Migration Validation
- [ ] Workflow activated successfully
- [ ] Test execution completes without errors
- [ ] Credentials authenticate correctly
- [ ] Webhooks respond properly
- [ ] Logging/monitoring active

## ✅ Post-Conditions
- [ ] Workflow active in target environment
- [ ] All tests passing
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented
- [ ] Migration logged for audit

## 🔗 Success Metrics
1. **Zero Downtime:** No interruption to existing workflows
2. **Complete Functionality:** All features work in new environment
3. **Clean Migration:** No dev artifacts in production
4. **Monitored:** Logging and alerts active

## 🚨 Error Handling

### Common Errors

1. **Missing Credentials in Target**
   - Cause: Credential not set up in target environment
   - Solution: Create and configure credential first
   - Prevention: Run credential audit before migration

2. **Webhook URL Conflicts**
   - Cause: Webhook path already exists in target
   - Solution: Use unique webhook paths per environment
   - Prevention: Follow naming convention (prefix with env)

3. **Node Version Mismatch**
   - Cause: Target environment has different node versions
   - Solution: Update nodes to compatible versions
   - Prevention: Keep environments in sync

### Rollback Procedure
If migration fails:
1. Deactivate migrated workflow immediately
2. Restore from backup: `PIPELINE_EXECUTE emergency-rollback`
3. Verify original environment still working
4. Investigate root cause
5. Fix issues and retry migration

## 📊 Output Format

### Migration Report
```markdown
# Workflow Migration Report
**Workflow:** Linda Master Orchestrator
**Source:** Development
**Target:** Production
**Date:** 2025-10-01 15:45:22
**Status:** ✅ SUCCESS

## Transformations Applied

### Credentials Remapped (5)
| Node | Credential Type | Dev ID | Prod ID |
|------|----------------|---------|----------|
| Supabase Insert | supabaseApi | dev_123 | prod_456 |
| Twilio SMS | twilioApi | dev_789 | prod_012 |
| OpenAI Chat | openAiApi | dev_345 | prod_678 |

### URLs Updated (3)
| Type | Dev URL | Prod URL |
|------|---------|----------|
| Webhook | https://...dev.../webhook/... | https://...prod.../webhook/... |

### Variables Changed (2)
| Variable | Dev Value | Prod Value |
|----------|-----------|------------|
| notification_phone | +1-555-TEST | +1-980-266-9595 |
| database | dev_db | production_db |

## Validation Results
✅ All 5 credentials verified in target
✅ All 3 webhook URLs valid
✅ No dev artifacts detected
✅ All expressions validated
✅ Test execution successful

## Post-Migration Tests
✅ Workflow activated
✅ Webhook responds (200 OK)
✅ First execution completed successfully
✅ Monitoring alerts configured
✅ Rollback plan documented

## Monitoring
- Workflow ID: wf_prod_12345
- Supabase logging: ACTIVE
- WhatsApp alerts: CONFIGURED (+1-980-266-9595)
- Performance baseline: 2.3s avg execution time

## Next Steps
1. Monitor for 24 hours
2. Run @performance-profile after 100 executions
3. Archive dev version if stable
4. Update documentation

*Migration completed by WORKFLOW_MIGRATE v1.0.0*
```

## 🔗 Combines Well With

### Before This Command
- **@workflow-validate** → **WORKFLOW_MIGRATE** (validate before migration)
- **@backup-versioned** → **WORKFLOW_MIGRATE** (safety backup)
- **@workflow-diff** → **WORKFLOW_MIGRATE** (understand changes)

### After This Command
- **WORKFLOW_MIGRATE** → **@performance-profile** (baseline performance)
- **WORKFLOW_MIGRATE** → **@dependency-map** (update architecture docs)

### Common Pipelines
1. **Safe Migration:** validate → backup → WORKFLOW_MIGRATE → performance-profile
2. **Full Deployment:** workflow-diff → validate → backup → WORKFLOW_MIGRATE → monitor

## 💡 Pro Tips
- Always test in staging before production
- Use environment prefixes for credentials (dev_, prod_)
- Keep environment mapping config in version control
- Document all environment-specific values
- Schedule migrations during low-traffic periods
- Have rollback plan ready before starting
- Monitor closely for first 24-48 hours after migration

## 🔖 Examples

### Example 1: Dev to Production
```
Input:
  Source: Development environment
  Workflow: Linda Master Orchestrator v2.3
  Target: Production
  
Actions:
  - Remap 5 credentials
  - Update 3 webhook URLs  
  - Change notification phone number
  - Update database references
  
Output: Workflow active in production with all prod credentials
```

### Example 2: Creating Staging Copy
```
Input:
  Source: Production
  Workflow: Dispatch Coordinator
  Target: Staging (for testing updates)
  
Actions:
  - Clone production workflow
  - Remap to staging credentials
  - Add "_staging" suffix to webhook paths
  - Disable production notifications
  
Output: Testing environment ready for updates
```

---

## 📚 Related Commands
- `workflow-validate` - Pre-migration validation
- `backup-versioned` - Safety backups
- `workflow-diff` - Compare environments
- `emergency-rollback` - Undo migration
- `credentials-manage` - Credential setup

## 📝 Version History
- **1.0.0** (2025-10-01): Initial migration engine with environment mapping

---

*Command Standard Version: 2.0.0*

