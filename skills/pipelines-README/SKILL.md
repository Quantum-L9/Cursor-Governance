---
name: pipelines-README
description: 🚀 Pipeline Command System
disable-model-invocation: true
---

# 🚀 Pipeline Command System

## 📖 Overview
This directory contains orchestrated multi-step pipelines that combine individual commands into powerful workflows. Each pipeline serves a specific stage of the development lifecycle.

---

## 🎯 The Core Sequence: From Discovery to Deployment

### The Master Pipeline (Rarely Used)

```yaml
000_full-deployment-from-scratch.md - "The Nuclear Option"
  Chains: 00 → 01 → 02 (all three stages)
  Duration: 30-43 minutes
  Risk: HIGH
  Use: Greenfield deployments, disaster recovery, client onboarding
  
⚠️ WARNING: 95% of work should use individual pipelines (00, 01, 02)
```

### The Three-Stage Journey (Most Common)

These three pipelines form the **modular workflow lifecycle**:

```
00 → DISCOVER → 01 → PREPARE → 02 → DEPLOY
   (Understand)    (Clean)       (Go Live)
```

```yaml
STAGE 1: DISCOVERY & UNDERSTANDING
  Pipeline: 00_project-initialize.md
  Duration: 12-18 minutes
  Risk: SAFE
  Goal: Comprehensive project understanding
  
STAGE 2: WORKFLOW PREPARATION  
  Pipeline: 01_workflow-prep-production.md
  Duration: 3-5 minutes
  Risk: SAFE
  Goal: Clean and validate n8n workflows
  
STAGE 3: PRODUCTION DEPLOYMENT
  Pipeline: 02_deploy-production.md
  Duration: 15-20 minutes
  Risk: HIGH
  Goal: Safe production deployment with monitoring
```

---

## 📚 Pipeline Reference

### Master Pipeline (Nuclear Option)

#### `000_full-deployment-from-scratch.md` - "The Nuclear Option"
**When to Use:**
- 🆕 Brand new project (first deployment ever)
- 🚨 Disaster recovery (complete rebuild)
- 👥 Client onboarding (initial setup)
- 🔄 Annual system refresh
- 🌐 Major platform migration

**What It Does:**
- Chains all 3 core pipelines: 00 → 01 → 02
- Complete end-to-end deployment
- Validation gates between stages
- Pause points for review
- Stage skipping capability

**Output:** Fully deployed, documented, monitored production system

**⚠️ WARNING:** 95% of work should use individual pipelines instead!

**Next Step:** Monitor and maintain (use `weekly-maintenance`)

---

### Core Sequence Pipelines (Numbered)

#### `00_project-initialize.md` - "First Day Protocol"
**When to Use:**
- 🆕 First time opening project
- 🏖️ Returning after long break (weeks/months)
- 👥 Onboarding new team members
- 🔍 Quarterly deep-dive reviews
- 🔧 Before major refactoring

**What It Does:**
1. Creates safety backup
2. Scans workspace structure
3. Maps dependencies & architecture
4. Validates all workflows
5. Verifies credentials & security
6. Runs comprehensive audit
7. Extracts successful patterns

**Output:** Complete project understanding, documentation, patterns

**Next Step:** → `01_workflow-prep-production` (when ready to prepare workflows)

---

#### `01_workflow-prep-production.md` - "n8n Workflow Prep"
**When to Use:**
- 📥 Before importing ANY workflow to n8n
- 🔧 After modifying workflows
- 📋 Before client/team handoff
- 🎯 As part of CI/CD for n8n

**What It Does:**
1. Cleans emojis from node names (prevents import errors)
2. Updates deprecated nodes
3. Validates structure & connections
4. Generates enterprise documentation
5. Creates versioned backup

**Output:** `workflow_CLEAN.json` files ready for import

**Next Step:** → `02_deploy-production` (when ready to go live)

---

#### `02_deploy-production.md` - "Production Deployment"
**When to Use:**
- 🚀 Deploying to live production
- 🔄 Monthly production updates
- ⚠️ After all validations pass
- 🎯 With change management approval

**What It Does:**
1. Pre-deployment audit
2. Safety backup
3. Final validation
4. Security audit
5. Credentials verification
6. **Actual deployment**
7. Performance profiling
8. Post-deployment monitoring

**Output:** Live production system with monitoring

**Next Step:** Monitor and maintain (use `weekly-maintenance`)

---

### Supporting Pipelines (Unnumbered)

#### `rapid-analysis.md` - Fast Analysis Without Full Init
**When:** Need quick analysis without full initialization
**Duration:** 5-8 minutes
**Use Case:** Quick health check, debug sessions, fast audits

---

#### `new-workflow-setup.md` - Scaffold New Workflow
**When:** Creating brand new n8n workflow
**Duration:** 3-5 minutes
**Use Case:** Boilerplate generation, standardized setup

---

#### `weekly-maintenance.md` - Ongoing Health Check
**When:** Weekly/bi-weekly maintenance
**Duration:** 5-10 minutes
**Use Case:** Preventive maintenance, catching issues early

---

#### `emergency-rollback.md` - Disaster Recovery
**When:** Production is broken, need immediate rollback
**Duration:** 2-5 minutes
**Risk:** MODERATE
**Use Case:** Emergency recovery, undo bad deployment

---

## 🎬 Complete Workflow Examples

### Example 1: New Project Start to Production

```bash
# Week 1: Day 1 - Understand the project
@00_project-initialize
# Output: Full understanding, patterns, documentation
# Time: 15 minutes

# Week 2-3: Development phase
# ... build and modify workflows ...

# Week 3: Prepare workflows for import
@01_workflow-prep-production MASTER_SALES_AGENT_PRODUCTION/**/*.json
# Output: Clean workflows ready for import
# Time: 5 minutes

# Week 3: Deploy to production
@02_deploy-production
# Output: Live production system
# Time: 18 minutes

# Ongoing: Weekly maintenance
@weekly-maintenance
# Output: Health reports, caught issues
# Time: 8 minutes/week
```

---

### Example 2: Emergency Fix Workflow

```bash
# Something broke in production!

# 1. Rollback immediately
@emergency-rollback
# Time: 3 minutes

# 2. Fix the issue locally

# 3. Prepare fixed workflow
@01_workflow-prep-production fixed_workflow.json
# Time: 3 minutes

# 4. Deploy fix
@02_deploy-production
# Time: 15 minutes

# 5. Verify fix
@rapid-analysis
# Time: 5 minutes
```

---

### Example 3: Quarterly Review & Optimization

```bash
# Every 3 months: Deep health check

# 1. Full project review
@00_project-initialize
# Rediscover what changed, update patterns
# Time: 15 minutes

# 2. Check all workflows
@01_workflow-prep-production **/*.json
# Ensure everything is still clean
# Time: 10 minutes (multiple files)

# 3. Optional: Refresh production
@02_deploy-production
# Deploy any improvements
# Time: 18 minutes
```

---

## 🎯 Decision Tree: Which Pipeline?

```
START HERE
    ↓
    
❓ What do you need to do?

├─ 🎬 "Brand new project - first deployment ever"
│  └─ Use: @000_full-deployment-from-scratch
│     Output: Complete system (discovery → prep → production)
│     Duration: 35-40 min
│     ⚠️ WARNING: Use ONLY for greenfield deployments!
│
├─ 🤔 "I don't understand this project"
│  └─ Use: @00_project-initialize
│     Output: Full understanding + documentation
│     Duration: 15 min
│
├─ 🔧 "I modified workflows, need to prepare for import"
│  └─ Use: @01_workflow-prep-production
│     Output: Clean .json files
│     Duration: 5 min
│
├─ 🚀 "Ready to deploy to production"
│  └─ Use: @02_deploy-production
│     Output: Live production system
│     Duration: 18 min
│
├─ ⚡ "Need quick health check"
│  └─ Use: @rapid-analysis
│     Output: Fast audit report
│     Duration: 6 min
│
├─ 🆕 "Starting new workflow from scratch"
│  └─ Use: @new-workflow-setup
│     Output: Boilerplate workflow
│     Duration: 4 min
│
├─ 🔄 "Weekly maintenance check"
│  └─ Use: @weekly-maintenance
│     Output: Health report
│     Duration: 8 min
│
└─ 🚨 "PRODUCTION IS BROKEN!"
   └─ Use: @emergency-rollback
      Output: Restored previous state
      Duration: 3 min
```

---

## 💡 Best Practices

### 1. Always Follow the Sequence (for new work)
```
00 → 01 → 02 → weekly-maintenance
```

Don't skip `00_project-initialize` even if tempting - it catches issues early.

### 2. Use Prep Before Every Import
```
Every single time you import to n8n:
  @01_workflow-prep-production workflow.json
```

The emoji cleaning alone saves hours of debugging.

### 3. Never Deploy Without Validation
```
Before @02_deploy-production:
  ✓ Ran @01_workflow-prep-production
  ✓ All validations passed
  ✓ Tested in dev environment
  ✓ Change management approved
```

### 4. Keep Backups Current
All numbered pipelines create backups automatically, but verify:
```bash
ls -lt Backup/ | head -5
```

Should see recent backups from each pipeline run.

### 5. Read the Reports
Each pipeline generates reports - actually read them:
- `00_project-initialize` → `Documentation/INITIALIZATION_REPORT.md`
- `01_workflow-prep-production` → Terminal output (comprehensive)
- `02_deploy-production` → `Deployment/DEPLOYMENT_REPORT.md`

---

## 🔗 Pipeline Dependencies

### What Each Pipeline Needs

**`00_project-initialize` requires:**
- ✅ Workspace cloned locally
- ✅ Basic read permissions
- ✅ Disk space for backup

**`01_workflow-prep-production` requires:**
- ✅ Valid workflow .json files
- ✅ Write permissions (creates _CLEAN.json)
- ✅ Python 3.x (for cleaning script)

**`02_deploy-production` requires:**
- ✅ All validations passed
- ✅ n8n instance accessible
- ✅ Production credentials configured
- ✅ Deployment approval obtained

---

## 🎨 Command Composition

### Creating Custom Pipelines

You can combine individual commands into custom pipelines:

```bash
# Custom lightweight deployment
PIPELINE_CUSTOM [
  workflow-validate,
  credentials-manage,
  deploy-to-n8n
]

# Custom deep analysis
PIPELINE_CUSTOM [
  workspace-scan,
  dependency-map,
  audit-full,
  pattern-extract
]

# Custom emergency prep
PIPELINE_CUSTOM [
  backup-versioned,
  clean-emojis,
  workflow-validate,
  deploy-to-n8n
]
```

---

## 📊 Success Metrics

### How to Know It's Working

**After `00_project-initialize`:**
- ✅ Can explain project architecture to colleague
- ✅ Know what's safe to modify
- ✅ Have dependency maps and patterns
- ✅ Confidence level: 8/10+

**After `01_workflow-prep-production`:**
- ✅ Have `workflow_CLEAN.json` files
- ✅ Zero emoji-related import errors
- ✅ All nodes up-to-date
- ✅ Ready to import: YES

**After `02_deploy-production`:**
- ✅ Production system live and responding
- ✅ No errors in first 5 minutes
- ✅ Monitoring configured
- ✅ Rollback plan ready

---

## 🚨 Common Issues & Solutions

### Issue: "Pipeline fails at Step X"

**Solution:**
1. Read the error message carefully
2. Check the specific command's documentation
3. Verify prerequisites are met
4. Try running that command individually
5. If still stuck, check the command's troubleshooting section

### Issue: "Too slow for daily work"

**Solution:**
- Don't use full pipelines daily
- Use individual commands instead:
  - Quick validation: `@workflow-validate`
  - Fast audit: `@rapid-analysis`
  - Emergency fix: Just fix and redeploy

### Issue: "Forgot which pipeline to use"

**Solution:**
- Check the Decision Tree above
- Ask yourself: "What stage am I in?"
  - Discovery → 00
  - Preparation → 01
  - Deployment → 02

---

## 🔄 Migration & Updates

### Updating Pipeline Commands

When individual commands are updated:
1. Pipelines automatically use latest versions
2. Check release notes for breaking changes
3. Test in dev before production

### Adding New Pipelines

Follow the numbering convention:
- `00-09`: Core sequence pipelines
- `10-19`: Specialized workflows
- `20-29`: Team-specific pipelines
- Unnumbered: Supporting/utility pipelines

---

## 📚 Related Documentation

- **Individual Commands:** `.cursor/commands/n8n/`
- **Core Commands:** `.cursor/commands/core/`
- **Framework:** `.cursor/commands/_framework/`
- **Analysis Tools:** `.cursor/commands/analysis/`
- **Infrastructure:** `.cursor/commands/infrastructure/`

---

## 🎯 Quick Reference

### Most Common Workflows

```bash
# RARE: Brand new project (complete deployment)
@000_full-deployment-from-scratch --pause-after-each

# COMMON: New project setup (understanding only)
@00_project-initialize

# COMMON: Prepare workflows for import
@01_workflow-prep-production *.json

# COMMON: Deploy to production
@02_deploy-production

# REGULAR: Weekly check
@weekly-maintenance

# EMERGENCY: Rollback
@emergency-rollback
```

### Decision Helper

```bash
# Ask yourself: "Have I deployed this project before?"
# 
# NO → First time ever
#   @000_full-deployment-from-scratch
#
# YES → Working on existing project
#   Use individual pipelines as needed:
#   @00_project-initialize       # Once per project/quarterly
#   @01_workflow-prep-production # Before each import
#   @02_deploy-production        # Monthly/as needed
```

---

## 💬 Philosophy

> "Automate the boring stuff, document the important stuff, make the dangerous stuff safe."

Each pipeline embodies:
- ✅ **Safety First** - Always backup before changes
- ✅ **Validation Gates** - Catch errors before deployment
- ✅ **Documentation** - Generate reports automatically
- ✅ **Rollback Ready** - Always have an escape route
- ✅ **Enterprise Grade** - Bulletproof for production [[memory:2510896]]

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial pipeline system documentation

---

*Pipeline System Documentation v1.0*  
*Last Updated: 2025-10-01*  
*Maintained by: Sales Agent - Mack Team*

