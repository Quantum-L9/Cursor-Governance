---
name: pipelines-000_full-deployment-from-scratch
description: 🚀 Full Deployment From Scratch - "The Nuclear Option"
disable-model-invocation: true
---

---
command: FULL_DEPLOYMENT_FROM_SCRATCH
version: 1.0.0
category: pipeline
tags: [master-pipeline, deployment, greenfield, end-to-end, nuclear-option, orchestration]
dependencies: [00_project-initialize, 01_workflow-prep-production, 02_deploy-production]
risk_level: HIGH
requires_backup: true
estimated_duration: 30-43min
complexity_score: 9
---

# 🚀 Full Deployment From Scratch - "The Nuclear Option"

## ⚠️ CRITICAL WARNING

**This is the MASTER PIPELINE that executes ALL THREE core stages in sequence.**

```
⏰ Duration: 30-43 minutes
⚠️ Risk Level: HIGH
🎯 Use Case: Greenfield deployments ONLY
💡 95% of work should use individual pipelines
```

**STOP AND READ:** Most of the time, you should use `00`, `01`, `02` individually, not this master pipeline.

---

## 📖 Purpose

The complete end-to-end deployment pipeline from "clone repository" to "live in production" - automated, validated, and bulletproof. This is the deployment equivalent of pushing the big red button that says "DO EVERYTHING."

Think of this as:
- 🏗️ Building a house from foundation to furniture in one go
- 🚀 Complete NASA launch sequence from pre-flight to orbit
- 🎬 Full movie production from script to premiere

---

## 🎯 What This Does

Executes the complete three-stage deployment sequence:

```yaml
STAGE 1: DISCOVERY & UNDERSTANDING
  Pipeline: 00_project-initialize
  Duration: 12-18 minutes
  Output: Complete project understanding + documentation
  
STAGE 2: WORKFLOW PREPARATION
  Pipeline: 01_workflow-prep-production
  Duration: 3-5 minutes
  Output: Clean, validated workflows ready for import
  
STAGE 3: PRODUCTION DEPLOYMENT
  Pipeline: 02_deploy-production
  Duration: 15-20 minutes
  Output: Live production system with monitoring

Total: 30-43 minutes (with validation gates between each)
```

---

## 🎪 When to Use This Pipeline

### ✅ DO USE (Rare Cases):

**1. Brand New Project - First Deployment Ever**
```
Situation: Just cloned repo, never deployed before
Outcome: From zero to production in 40 minutes
Frequency: Once per project
```

**2. Disaster Recovery - Complete Rebuild**
```
Situation: Production destroyed, rebuilding from backup
Outcome: Complete system restoration
Frequency: Hopefully never
```

**3. Client Onboarding - Initial Setup**
```
Situation: New client, setting up their entire system
Outcome: Fully configured, documented, deployed system
Frequency: Per new client
```

**4. Annual System Refresh**
```
Situation: Yearly complete re-initialization
Outcome: Fresh start with updated patterns
Frequency: Annually
```

**5. Major Platform Migration**
```
Situation: Moving to new n8n instance/infrastructure
Outcome: Complete validated migration
Frequency: Very rare
```

---

### ❌ DON'T USE (Most Cases):

**These scenarios should use individual pipelines:**

```yaml
Daily Development:
  ❌ Don't use: 000_full-deployment
  ✅ Use instead: Individual pipelines as needed
  
Workflow Updates:
  ❌ Don't use: 000_full-deployment (too slow)
  ✅ Use instead: 01_workflow-prep-production
  
Monthly Production Deploys:
  ❌ Don't use: 000_full-deployment (unnecessary init)
  ✅ Use instead: 02_deploy-production
  
Emergency Fixes:
  ❌ Don't use: 000_full-deployment (way too slow)
  ✅ Use instead: emergency-rollback + individual fixes
  
Returning After Break:
  ❌ Don't use: 000_full-deployment (no deploy needed)
  ✅ Use instead: 00_project-initialize
```

---

## 🚀 Execution Modes

### Mode 1: Full Nuclear Option (Rare)

```bash
@000_full-deployment-from-scratch
```

**Runs:** All 3 stages, no pauses, no skips  
**Duration:** 30-43 minutes  
**Use When:** Brand new project, complete rebuild

---

### Mode 2: With Stage Skipping (More Common)

```bash
# Already initialized, skip discovery
@000_full-deployment-from-scratch --skip-stage-1

# Already initialized and prepped
@000_full-deployment-from-scratch --skip-stage-1 --skip-stage-2

# Only run initialization and prep (no deploy)
@000_full-deployment-from-scratch --skip-stage-3
```

**Use When:** Some stages already completed

---

### Mode 3: With Pause Points (Recommended First Time)

```bash
@000_full-deployment-from-scratch --pause-after-each
```

**Output:**
```
✅ Stage 1 Complete: Project initialized
📊 Review: Documentation/INITIALIZATION_REPORT.md

Continue to Stage 2? [Y/n]: _
```

**Use When:** First time running, want to review between stages

---

### Mode 4: Dry Run (See What Would Happen)

```bash
@000_full-deployment-from-scratch --dry-run
```

**Output:**
```
DRY RUN MODE - No changes will be made

Would execute:
  Stage 1: 00_project-initialize
  Stage 2: 01_workflow-prep-production
  Stage 3: 02_deploy-production
  
Estimated duration: 35 minutes
Risk level: HIGH
```

**Use When:** Planning deployment, want to verify sequence

---

### Mode 5: Specific Workflow Only

```bash
@000_full-deployment-from-scratch --workflow="master_orchestrator.json"
```

**Use When:** Deploying single workflow through full pipeline

---

## 💻 Implementation

### Master Pipeline Orchestrator

```python
#!/usr/bin/env python3
"""
Full Deployment From Scratch - Master Pipeline
Chains 00 → 01 → 02 with validation gates
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

class MasterDeploymentPipeline:
    def __init__(self, args):
        self.args = args
        self.skip_stage_1 = '--skip-stage-1' in args
        self.skip_stage_2 = '--skip-stage-2' in args
        self.skip_stage_3 = '--skip-stage-3' in args
        self.pause_after_each = '--pause-after-each' in args
        self.dry_run = '--dry-run' in args
        
        self.start_time = datetime.now()
        self.stages_completed = []
        self.errors = []
        
    def log(self, message, level="INFO"):
        """Log pipeline progress"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        elapsed = (datetime.now() - self.start_time).seconds
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARN": "⚠️",
            "ERROR": "❌",
            "STAGE": "🔄",
            "GATE": "🚦"
        }.get(level, "•")
        print(f"[{timestamp}] [{elapsed}s] {prefix} {message}")
    
    def show_warning(self):
        """Display critical warning before starting"""
        print("\n" + "="*70)
        print("⚠️  CRITICAL WARNING: MASTER PIPELINE")
        print("="*70)
        print("\nYou are about to run the COMPLETE deployment sequence:")
        print("  Stage 1: Project initialization (12-18 min)")
        print("  Stage 2: Workflow preparation (3-5 min)")
        print("  Stage 3: Production deployment (15-20 min)")
        print("\nTotal Duration: 30-43 minutes")
        print("Risk Level: HIGH")
        print("\n⚠️  MOST WORK SHOULD USE INDIVIDUAL PIPELINES")
        print("="*70)
        
        if not self.dry_run:
            response = input("\nAre you SURE you need the full pipeline? [y/N]: ")
            if response.lower() != 'y':
                print("\n✅ Good call. Use individual pipelines instead:")
                print("  @00_project-initialize       # Discovery")
                print("  @01_workflow-prep-production # Preparation")
                print("  @02_deploy-production        # Deployment")
                sys.exit(0)
    
    def run_stage(self, stage_num, stage_name, command):
        """Execute a pipeline stage"""
        if self.dry_run:
            self.log(f"Would run Stage {stage_num}: {stage_name}", "INFO")
            return True
        
        self.log(f"Starting Stage {stage_num}: {stage_name}", "STAGE")
        
        try:
            # Run the command (simplified - would use actual pipeline execution)
            result = subprocess.run(
                [command],
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.log(f"Stage {stage_num} Complete: {stage_name}", "SUCCESS")
                self.stages_completed.append(stage_num)
                return True
            else:
                self.log(f"Stage {stage_num} Failed: {stage_name}", "ERROR")
                self.errors.append(f"Stage {stage_num}: {result.stderr}")
                return False
                
        except Exception as e:
            self.log(f"Stage {stage_num} Error: {str(e)}", "ERROR")
            self.errors.append(f"Stage {stage_num}: {str(e)}")
            return False
    
    def validation_gate(self, stage_num):
        """Validation gate between stages"""
        self.log(f"Validation Gate {stage_num}", "GATE")
        
        if self.pause_after_each and not self.dry_run:
            print("\n" + "-"*70)
            print(f"✅ Stage {stage_num} Complete")
            print(f"Review reports before continuing...")
            print("-"*70)
            response = input(f"\nContinue to Stage {stage_num + 1}? [Y/n]: ")
            if response.lower() == 'n':
                self.log("Pipeline paused by user", "WARN")
                return False
        
        return True
    
    def run(self):
        """Execute the master pipeline"""
        print("\n" + "="*70)
        print("🚀 FULL DEPLOYMENT FROM SCRATCH - MASTER PIPELINE")
        print("="*70)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE EXECUTION'}")
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
        # Show warning
        self.show_warning()
        
        # Stage 1: Project Initialize
        if not self.skip_stage_1:
            if not self.run_stage(1, "Project Initialize", "@00_project-initialize"):
                return self.generate_report(success=False)
            if not self.validation_gate(1):
                return self.generate_report(success=False, paused=True)
        else:
            self.log("Stage 1 SKIPPED (--skip-stage-1)", "WARN")
        
        # Stage 2: Workflow Prep
        if not self.skip_stage_2:
            if not self.run_stage(2, "Workflow Prep", "@01_workflow-prep-production"):
                return self.generate_report(success=False)
            if not self.validation_gate(2):
                return self.generate_report(success=False, paused=True)
        else:
            self.log("Stage 2 SKIPPED (--skip-stage-2)", "WARN")
        
        # Stage 3: Deploy Production
        if not self.skip_stage_3:
            if not self.run_stage(3, "Deploy Production", "@02_deploy-production"):
                return self.generate_report(success=False)
        else:
            self.log("Stage 3 SKIPPED (--skip-stage-3)", "WARN")
        
        return self.generate_report(success=True)
    
    def generate_report(self, success, paused=False):
        """Generate final pipeline report"""
        elapsed = (datetime.now() - self.start_time).seconds
        
        print("\n" + "="*70)
        print("📊 MASTER PIPELINE EXECUTION REPORT")
        print("="*70)
        
        if self.dry_run:
            print("\nMode: DRY RUN (no changes made)")
        elif paused:
            status = "⏸️  PAUSED BY USER"
        elif success and not self.errors:
            status = "✅ SUCCESS - FULLY DEPLOYED"
        else:
            status = "❌ FAILED - REQUIRES ATTENTION"
        
        print(f"\nStatus: {status}")
        print(f"Duration: {elapsed // 60} minutes {elapsed % 60} seconds")
        print(f"Stages Completed: {len(self.stages_completed)}/3")
        
        if not self.skip_stage_1:
            state = "✅" if 1 in self.stages_completed else "❌"
            print(f"  {state} Stage 1: Project Initialize")
        if not self.skip_stage_2:
            state = "✅" if 2 in self.stages_completed else "❌"
            print(f"  {state} Stage 2: Workflow Prep")
        if not self.skip_stage_3:
            state = "✅" if 3 in self.stages_completed else "❌"
            print(f"  {state} Stage 3: Deploy Production")
        
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        
        if success and not self.errors and not paused and not self.dry_run:
            print("\n✅ DEPLOYMENT COMPLETE")
            print("\nYour system is now:")
            print("  ✅ Fully understood (documentation generated)")
            print("  ✅ Workflows cleaned and validated")
            print("  ✅ Live in production with monitoring")
            print("\nNext Steps:")
            print("  1. Verify production system is responding")
            print("  2. Run smoke tests on critical paths")
            print("  3. Monitor for first 24 hours")
            print("  4. Schedule @weekly-maintenance")
        elif paused:
            print("\nPipeline paused. To resume:")
            print("  @000_full-deployment-from-scratch --skip-completed-stages")
        elif not success:
            print("\n🔧 Action Required:")
            print("  1. Review errors above")
            print("  2. Fix issues in failed stage")
            print("  3. Re-run from failed stage")
            print("  4. Or run stages individually")
        
        print("\n" + "="*70 + "\n")
        
        return 0 if success and not self.errors and not paused else 1

if __name__ == "__main__":
    pipeline = MasterDeploymentPipeline(sys.argv[1:])
    sys.exit(pipeline.run())
```

---

## 📋 Usage Examples

### Example 1: First Deployment (Brand New Project)

```bash
# This is the ONLY time you should use full pipeline without skips
@000_full-deployment-from-scratch --pause-after-each

# Output:
# Stage 1 Complete → Review initialization report
# [Pause] Continue? Y
# Stage 2 Complete → Review cleaned workflows
# [Pause] Continue? Y
# Stage 3 Complete → Production is live

# Total time: ~35 minutes
```

---

### Example 2: Already Initialized, Just Deploy

```bash
# You ran 00_project-initialize yesterday
@000_full-deployment-from-scratch --skip-stage-1

# Runs: Stage 2 + Stage 3
# Time saved: 15 minutes
```

---

### Example 3: Disaster Recovery

```bash
# Production is destroyed, rebuilding everything
@000_full-deployment-from-scratch

# Full nuclear option - no skips
# Time: 40 minutes
# Outcome: Complete system restoration
```

---

### Example 4: Planning Mode (Dry Run)

```bash
# See what would happen without executing
@000_full-deployment-from-scratch --dry-run

# Output:
# Would run Stage 1: 00_project-initialize (15 min)
# Would run Stage 2: 01_workflow-prep-production (5 min)
# Would run Stage 3: 02_deploy-production (18 min)
# Total: ~38 minutes
```

---

## ⏱️ Expected Timeline

### Full Pipeline (No Skips)

```
⏱️  00:00 → Pipeline Start

Stage 1: Project Initialize
⏱️  00:01 → Backup created
⏱️  00:03 → Workspace scanned
⏱️  00:08 → Dependencies mapped
⏱️  00:10 → Workflows validated
⏱️  00:11 → Credentials verified
⏱️  00:14 → Audit complete
⏱️  00:15 → Patterns extracted
[GATE 1] → Review initialization report

Stage 2: Workflow Prep
⏱️  00:16 → Emojis cleaned
⏱️  00:17 → Nodes updated
⏱️  00:18 → Workflows validated
⏱️  00:19 → Documentation generated
⏱️  00:20 → Backup created
[GATE 2] → Review cleaned workflows

Stage 3: Deploy Production
⏱️  00:21 → Pre-deployment audit
⏱️  00:24 → Safety backup
⏱️  00:25 → Final validation
⏱️  00:26 → Security audit
⏱️  00:28 → Credentials verified
⏱️  00:29 → DEPLOYING TO PRODUCTION
⏱️  00:34 → Performance profiled
⏱️  00:38 → Monitoring configured

⏱️  00:38 → COMPLETE ✅

Total: 38 minutes
```

---

## 🚨 Error Handling & Rollback

### If Stage 1 Fails (Rare)
```
Impact: No changes made yet
Action: Fix issue, re-run
Rollback: Not needed (no changes)
```

### If Stage 2 Fails
```
Impact: Project initialized but workflows not ready
Action: Fix workflows, run @01_workflow-prep-production
Rollback: Not needed (only documentation affected)
Next Run: @000_full-deployment-from-scratch --skip-stage-1
```

### If Stage 3 Fails (Critical)
```
Impact: Production deployment failed
Action: Run @emergency-rollback immediately
Rollback: Restore previous production state
Fix: Address deployment issues
Next Run: @02_deploy-production (or @000 --skip-stage-1 --skip-stage-2)
```

---

## 🔗 Integration Points

### Before This Pipeline
```yaml
Prerequisites:
  ✅ Repository cloned
  ✅ Environment variables configured
  ✅ n8n instance accessible
  ✅ Credentials ready
  ✅ Deployment approval obtained
  ✅ Change window scheduled
```

### After This Pipeline
```yaml
Next Steps:
  1. Verify production system responding
  2. Run smoke tests
  3. Monitor for 24 hours
  4. Schedule @weekly-maintenance
  5. Document any issues found
```

---

## 💡 Pro Tips

### 1. Almost Always Use Individual Pipelines
```bash
# 95% of your work should be:
@00_project-initialize       # Once per project
@01_workflow-prep-production # Before each import
@02_deploy-production        # Monthly deploys

# NOT the master pipeline
```

### 2. Use Dry Run First
```bash
# Always test the sequence first
@000_full-deployment-from-scratch --dry-run
```

### 3. Pause After Each Stage (First Time)
```bash
# Review between stages
@000_full-deployment-from-scratch --pause-after-each
```

### 4. Skip Completed Stages
```bash
# Don't re-run what's already done
@000_full-deployment-from-scratch --skip-stage-1
```

### 5. Have Rollback Plan Ready
```bash
# Before running, verify rollback works
@emergency-rollback --verify-only
```

---

## 🎯 Success Metrics

After successful completion:

**Stage 1 Complete:**
- ✅ Full project understanding
- ✅ Documentation generated
- ✅ Patterns extracted
- ✅ Architecture mapped

**Stage 2 Complete:**
- ✅ Workflows cleaned
- ✅ Nodes updated
- ✅ Ready for import
- ✅ Documentation added

**Stage 3 Complete:**
- ✅ Production is live
- ✅ Monitoring active
- ✅ Performance baselined
- ✅ Rollback tested

**Overall:**
- ✅ From clone to production in <45 min
- ✅ Fully documented
- ✅ Fully validated
- ✅ Production-ready

---

## 📊 When to Use What

### Decision Matrix

```yaml
Scenario: "Brand new project, first deployment"
  Use: 000_full-deployment-from-scratch
  Reason: Need everything from scratch
  
Scenario: "Working on existing project"
  Use: Individual pipelines (00, 01, 02)
  Reason: Only run what you need
  
Scenario: "Quick workflow update"
  Use: 01_workflow-prep-production
  Reason: Just need prep, not full deployment
  
Scenario: "Monthly production deploy"
  Use: 02_deploy-production
  Reason: Already initialized and prepped
  
Scenario: "Disaster recovery"
  Use: 000_full-deployment-from-scratch
  Reason: Complete rebuild needed
  
Scenario: "Client onboarding"
  Use: 000_full-deployment-from-scratch --pause-after-each
  Reason: Need complete setup with review points
```

---

## 🎓 Real-World Use Cases

### Use Case 1: Startup Launch Day

```
Company: New SaaS startup
Task: Deploy Linda Agent for first client
Timeline: Launch in 2 hours

9:00 AM: @000_full-deployment-from-scratch --pause-after-each
9:15 AM: Review initialization report ✅
9:20 AM: Review cleaned workflows ✅
9:38 AM: Production deployed ✅
9:45 AM: Smoke tests complete ✅
10:00 AM: Client presentation ready 🎉

Result: Bulletproof deployment, confident demo
```

### Use Case 2: Disaster Recovery

```
Scenario: Production server failed, data corrupted
Action: Restore from backup + redeploy

11:00 AM: Incident detected 🚨
11:05 AM: @emergency-rollback (temporary fix)
11:10 AM: Restore backup files
11:15 AM: @000_full-deployment-from-scratch
11:55 AM: Full system restored ✅
12:00 PM: Monitor for stability

Result: <1 hour downtime, complete recovery
```

### Use Case 3: Agency Client Onboarding

```
Agency: Automation agency
Client: New freight brokerage client
Task: Set up complete system

Week 1: Discovery & customization
Week 2: Ready to deploy

Deploy Day:
@000_full-deployment-from-scratch --pause-after-each

Stage 1: Show client documentation ✅
Stage 2: Demo workflow structure ✅  
Stage 3: Launch production system ✅

Result: Client confidence 10/10, smooth handoff
```

---

## ⚠️ Common Mistakes

### Mistake 1: Using It For Daily Work
```
❌ Wrong: Running 000 every time you make changes
✅ Right: Use individual pipelines for daily work
```

### Mistake 2: Not Using Dry Run First
```
❌ Wrong: Running live without testing
✅ Right: @000 --dry-run first, then live
```

### Mistake 3: No Rollback Plan
```
❌ Wrong: Deploy without rollback capability
✅ Right: Test rollback before deploying
```

### Mistake 4: Ignoring Pause Points
```
❌ Wrong: Running all 3 stages without review
✅ Right: --pause-after-each on first run
```

### Mistake 5: Skipping Prerequisites
```
❌ Wrong: Running without credentials configured
✅ Right: Verify all prerequisites first
```

---

## 📚 Related Commands

**Core Sequence:**
- `00_project-initialize` - Stage 1 only
- `01_workflow-prep-production` - Stage 2 only
- `02_deploy-production` - Stage 3 only

**Supporting Commands:**
- `rapid-analysis` - Quick audit without deployment
- `emergency-rollback` - Undo bad deployment
- `weekly-maintenance` - Ongoing health checks

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial master pipeline - chains 00 → 01 → 02 with gates

---

*Master Pipeline - The Nuclear Option*  
*Use Responsibly - Most Work Doesn't Need This*  
*Bulletproof From Clone to Production* [[memory:2510896]]

