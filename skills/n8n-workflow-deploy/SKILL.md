---
name: n8n-workflow-deploy
description: 🚀 Workflow Deploy - Deploy to n8n Instance
disable-model-invocation: true
---

---
command: WORKFLOW_DEPLOY
version: 1.0.0
category: n8n
tags: [deployment, n8n, workflows, production, activation]
dependencies: [workflow-validate, backup-versioned]
risk_level: moderate
requires_backup: true
estimated_duration: 1-2min
---

# 🚀 Workflow Deploy - Deploy to n8n Instance

## 📖 Purpose
Deploy validated workflows to n8n production instance. Handles upload, activation, verification, and logging. Safe deployment with rollback capability.

## 🎪 When to Use
- **Deploying new workflows** - After validation and testing
- **Updating existing workflows** - Push changes to production
- **Activating workflows** - Enable workflows in n8n
- **Batch deployment** - Deploy multiple workflows at once

## ⚠️ Pre-Conditions
- ✅ Workflows validated with @workflow-validate
- ✅ Backup created with @backup-versioned
- ✅ n8n instance accessible (https://ibeylin.app.n8n.cloud)
- ✅ N8N_API_KEY configured in environment

## 🚀 Execution

### Step 1: Pre-Deployment Check (15 sec)
```yaml
Verify:
  ✅ n8n instance reachable
  ✅ API key valid
  ✅ Workflows validated
  ✅ Backup exists
  ✅ No active executions (optional)
```

### Step 2: Upload Workflows (30-60 sec)
```bash
For each workflow:
  1. Read workflow JSON
  2. POST to n8n API /workflows
  3. Verify upload success
  4. Log workflow ID
  5. Store deployment timestamp
```

**API Endpoint:**
```
POST https://ibeylin.app.n8n.cloud/api/v1/workflows
Headers:
  X-N8N-API-KEY: {{$env.N8N_API_KEY}}
  Content-Type: application/json
Body: {workflow JSON}
```

### Step 3: Activate Workflows (15 sec)
```bash
For each uploaded workflow:
  1. PATCH /workflows/{id}
  2. Set active: true
  3. Verify activation
  4. Test webhook (if applicable)
```

### Step 4: Verification (15 sec)
```yaml
Verify deployment:
  ✅ All workflows uploaded
  ✅ All workflows activated
  ✅ Webhook URLs responding
  ✅ No errors in n8n UI
  ✅ Deployment logged to Supabase
```

### Step 5: Logging [[memory:2516763]]
```sql
INSERT INTO deployment_log (
  timestamp,
  workflow_name,
  workflow_id,
  version,
  deployed_by,
  status,
  n8n_url
) VALUES (...);
```

---

## 📊 Output Format

```markdown
# 🚀 Workflow Deployment Report

**Time:** 2025-10-01 15:30:00
**Target:** https://ibeylin.app.n8n.cloud
**Status:** ✅ SUCCESS

## Deployed Workflows (3)

| Workflow | ID | Status | Webhook |
|----------|-----|--------|---------|
| Lead Qualification v3.0 | wf_12345 | ✅ Active | /webhook/lead-qual |
| Material Classification v3.0 | wf_12346 | ✅ Active | /webhook/material |
| Buyer Matching v3.0 | wf_12347 | ✅ Active | /webhook/buyer-match |

## Verification Results

### Webhook Tests
- ✅ /webhook/lead-qual → 200 OK (145ms)
- ✅ /webhook/material → 200 OK (132ms)
- ✅ /webhook/buyer-match → 200 OK (156ms)

### n8n Instance Status
- ✅ All workflows visible in UI
- ✅ All workflows showing "Active"
- ✅ No errors in workflow list
- ✅ Execution history clean

### Supabase Logging
- ✅ 3 deployment records created
- ✅ Timestamps recorded
- ✅ Webhook URLs logged

## Deployment Summary

**Total Time:** 1m 45s
**Success Rate:** 100% (3/3)
**Rollback Available:** Yes (backup created)
**Next Steps:** Monitor first executions

## Monitoring Commands

```bash
# Check deployment status
@health-check

# Monitor performance
@performance-profile

# View execution logs
Open: https://ibeylin.app.n8n.cloud/workflows
```

---

**Deployment ID:** deploy_20251001_153000
**Deployed By:** WORKFLOW_DEPLOY v1.0.0
**Rollback:** @emergency-rollback --deployment=deploy_20251001_153000
```

---

## 🔧 Deployment Options

### Standard Deployment
```bash
@workflow-deploy
# Deploys all workflows in MASTER_SALES_AGENT_PRODUCTION/04_WORKFLOWS/01_N8N_WORKFLOWS/
```

### Selective Deployment
```bash
@workflow-deploy --workflows="lead-qualification,buyer-matching"
# Deploy only specified workflows
```

### Dry Run
```bash
@workflow-deploy --dry-run
# Simulate deployment without actually deploying
```

### Activate Only
```bash
@workflow-deploy --activate-only
# Only activate existing workflows (don't upload)
```

---

## ⚠️ Error Handling [[memory:2510896]]

### Common Errors & Solutions

**Error: API Key Invalid**
```bash
Solution:
  1. Verify N8N_API_KEY in .env
  2. Check key hasn't expired
  3. Test: curl -H "X-N8N-API-KEY: $KEY" https://ibeylin.app.n8n.cloud/api/v1/workflows
```

**Error: Workflow Already Exists**
```bash
Solution:
  1. Update existing workflow instead
  2. Or delete old workflow first
  3. Or use --force flag to overwrite
```

**Error: Webhook URL Conflict**
```bash
Solution:
  1. Check for duplicate webhook paths
  2. Deactivate conflicting workflow
  3. Update webhook path in one workflow
```

**Error: n8n Instance Unreachable**
```bash
Solution:
  1. Check internet connectivity
  2. Verify n8n instance is running
  3. Check firewall/VPN settings
  4. Contact n8n support if persistent
```

### Automatic Rollback Triggers
```yaml
Rollback if:
  - Upload fails for any workflow
  - Activation fails for any workflow
  - Webhook test fails
  - Critical error during deployment
```

---

## 🔗 Combines Well With

### Standard Deployment Flow
```bash
1. @workflow-validate    # Validate all workflows
2. @test-workflows       # Test workflows
3. @backup-versioned     # Create safety backup
4. @workflow-deploy      # Deploy to n8n
5. @health-check         # Verify deployment
```

### Emergency Deployment
```bash
1. @workflow-validate    # Quick validation
2. @workflow-deploy --force  # Force deploy
3. @health-check         # Immediate verification
```

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial workflow deployment command for n8n

---

*Command Standard Version: 2.0.0*
*Deploy with Confidence - Rollback with Ease*

