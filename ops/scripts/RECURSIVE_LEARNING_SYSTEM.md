---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "DOC-RLS-001"
component_name: "Recursive Learning System Documentation"
layer: "documentation"
domain: "learning"
type: "guide"
status: "active"
created: "2025-11-17T22:06:00Z"
updated: "2025-11-17T22:06:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"
---

# Recursive Learning System - Complete Guide

## Overview

The Recursive Learning System is a fully autonomous, self-improving governance system that continuously learns from mistakes, prevents repetition, and optimizes its own performance. It operates completely in the background without manual intervention.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Recursive Learning System                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐            │
│  │ Pre-Execution     │───▶│ Prevention       │            │
│  │ Checker           │    │ Effectiveness    │            │
│  │ (Real-time)       │    │ Tracker          │            │
│  └──────────────────┘    └──────────────────┘            │
│         │                         │                        │
│         ▼                         ▼                        │
│  ┌──────────────────┐    ┌──────────────────┐            │
│  │ Closed-Loop       │◀───│ Memory            │            │
│  │ Improvement       │    │ Compounding      │            │
│  │ (Hourly)          │    │ (Hourly)          │            │
│  └──────────────────┘    └──────────────────┘            │
│         │                         │                        │
│         └─────────┬───────────────┘                        │
│                   ▼                                        │
│         ┌──────────────────┐                              │
│         │ Orchestrator     │                              │
│         │ (Hourly)          │                              │
│         └──────────────────┘                              │
│                   │                                        │
│                   ▼                                        │
│         ┌──────────────────┐                              │
│         │ Health Monitor    │                              │
│         │ (Hourly)          │                              │
│         └──────────────────┘                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Pre-Execution Checker (OPS-PEC-001)

**Purpose:** Block actions that match known mistakes before execution

**How It Works:**
- Loads lessons from `repeated-mistakes.md`
- Builds pattern cache for fast matching
- Checks action descriptions against mistake patterns
- Blocks CRITICAL and HIGH severity mistakes
- Logs all checks to audit log

**Installation:**
```bash
cd ~/.cursor-governance
bash ops/scripts/install_pre_execution_checker.sh
```

**Usage:**
```bash
# Test checker
python3 ops/scripts/pre_execution_checker.py "create new script without searching"

# Refresh cache manually
python3 ops/scripts/pre_execution_checker.py
```

**Output:**
- Pattern cache: `ops/scripts/pre_execution_checker_config.json`
- Audit log: `ops/logs/pre_execution_checker_audit.jsonl`

### 2. Prevention Effectiveness Tracker (OPS-PET-001)

**Purpose:** Measure if lessons actually prevent mistakes

**How It Works:**
- Tracks prevention attempts from audit log
- Calculates prevention rate (blocked / total attempts)
- Measures mistake repetition rate
- Calculates lesson effectiveness per lesson
- Generates daily reports and weekly trend analysis

**Installation:**
```bash
cd ~/.cursor-governance
bash ops/scripts/install_prevention_effectiveness_tracker.sh
```

**Usage:**
```bash
# Calculate metrics
python3 ops/scripts/prevention_effectiveness_tracker.py --calculate

# Generate daily report
python3 ops/scripts/prevention_effectiveness_tracker.py --daily-report

# Generate weekly trend analysis
python3 ops/scripts/prevention_effectiveness_tracker.py --weekly-trend
```

**Output:**
- Metrics: `ops/logs/effectiveness_metrics.json`
- Daily reports: `ops/logs/effectiveness_reports/effectiveness_report_YYYYMMDD.md`
- Weekly trends: `ops/logs/effectiveness_reports/weekly_trend_YYYYMMDD.md`

### 3. Closed-Loop Improvement (OPS-CLI-001)

**Purpose:** Continuous self-improvement through observe-compare-adjust-validate-document cycle

**How It Works:**
1. **Observe:** Collect current metrics
2. **Compare:** Compare vs targets and historical data
3. **Adjust:** Generate adjustments based on gaps
4. **Validate:** Check if adjustments improved metrics
5. **Document:** Log all changes

**Installation:**
```bash
cd ~/.cursor-governance
bash ops/scripts/install_closed_loop_improvement.sh
```

**Usage:**
```bash
# Run improvement cycle
python3 ops/scripts/closed_loop_improvement.py --cycle

# Generate snapshot
python3 ops/scripts/closed_loop_improvement.py --snapshot
```

**Output:**
- Improvement log: `ops/logs/improvement_log.json`
- Snapshots: `ops/logs/improvement_snapshots/snapshot_YYYYMMDD_HHMMSS.json`

### 4. Memory Compounding System (OPS-MCS-001)

**Purpose:** Weight patterns by success/failure and auto-apply high-confidence patterns

**How It Works:**
- Tracks pattern weights (+1.0 success, +0.5 partial, -1.0 failure)
- Auto-applies patterns with weight >= 5.0
- Prunes patterns with weight < 0.30
- Evolves patterns (decay unused, merge similar)

**Installation:**
```bash
cd ~/.cursor-governance
bash ops/scripts/install_memory_compounding.sh
```

**Usage:**
```bash
# Initialize weights from memory
python3 ops/scripts/memory_compounding.py --initialize

# Evolve patterns (decay, merge)
python3 ops/scripts/memory_compounding.py --evolve

# Prune low-weight patterns
python3 ops/scripts/memory_compounding.py --prune

# Show statistics
python3 ops/scripts/memory_compounding.py --stats
```

**Output:**
- Pattern weights: `ops/logs/pattern_weights.json`
- Auto-applied patterns log: `ops/logs/auto_applied_patterns.jsonl`

### 5. Recursive Learning Orchestrator (OPS-RLS-001)

**Purpose:** Coordinate all recursive learning components

**How It Works:**
- Refreshes pre-execution checker cache
- Calculates effectiveness metrics
- Runs closed-loop improvement cycle
- Updates memory compounding
- Checks component health

**Installation:**
```bash
cd ~/.cursor-governance
bash ops/scripts/install_recursive_learning_orchestrator.sh
```

**Usage:**
```bash
# Run orchestration
python3 ops/scripts/recursive_learning_orchestrator.py
```

**Output:**
- System status: `ops/logs/recursive_learning_status.json`
- Log: `ops/logs/recursive_learning_orchestrator.log`

### 6. Health Monitor (OPS-HM-001)

**Purpose:** Monitor health of all components and auto-recover on failure

**How It Works:**
- Checks LaunchAgent status for all components
- Verifies log freshness
- Auto-recovers failed components
- Logs recovery attempts

**Installation:**
```bash
# Install as LaunchAgent (hourly health checks)
# Add to install script if needed
```

**Usage:**
```bash
# Run health check
python3 ops/scripts/recursive_learning_health_monitor.py
```

**Output:**
- Recovery log: `ops/logs/health_monitor_recovery.log`

## Installation

### Master Installer (All Components)

```bash
cd ~/.cursor-governance

# Install all LaunchAgents
bash ops/scripts/install_pre_execution_checker.sh
bash ops/scripts/install_prevention_effectiveness_tracker.sh
bash ops/scripts/install_closed_loop_improvement.sh
bash ops/scripts/install_memory_compounding.sh
bash ops/scripts/install_recursive_learning_orchestrator.sh

# Verify installation
launchctl list | grep cursor
```

### Verify All Components Running

```bash
# Check LaunchAgent status
launchctl list | grep -E "cursor\.(pre-execution|prevention|closed-loop|memory|recursive)"

# Expected output (all should show status 0):
# - com.cursor.pre-execution-checker
# - com.cursor.prevention-effectiveness-tracker
# - com.cursor.closed-loop-improvement
# - com.cursor.memory-compounding
# - com.cursor.recursive-learning-orchestrator
```

## Integration with Learning Pipeline

The recursive learning system integrates with the existing learning pipeline:

```bash
# process_learnings.sh now includes:
# Step 5: Refresh pre-execution checker cache
# Step 6: Update memory compounding weights
```

## Monitoring

### Check System Health

```bash
# Run health monitor
python3 ~/.cursor-governance/ops/scripts/recursive_learning_health_monitor.py

# Check logs
tail -50 ~/.cursor-governance/ops/logs/recursive_learning_orchestrator.log
```

### View Effectiveness Metrics

```bash
# View effectiveness metrics
cat ~/.cursor-governance/ops/logs/effectiveness_metrics.json | python3 -m json.tool

# View latest daily report
ls -t ~/.cursor-governance/ops/logs/effectiveness_reports/ | head -1 | xargs cat
```

### View Pattern Weights

```bash
# View pattern weights
cat ~/.cursor-governance/ops/logs/pattern_weights.json | python3 -m json.tool

# View auto-applied patterns
tail -20 ~/.cursor-governance/ops/logs/auto_applied_patterns.jsonl
```

## Troubleshooting

### Component Not Running

```bash
# Check LaunchAgent status
launchctl list | grep cursor.pre-execution-checker

# Reload if needed
launchctl unload ~/Library/LaunchAgents/com.cursor.pre-execution-checker.plist
launchctl load ~/Library/LaunchAgents/com.cursor.pre-execution-checker.plist
```

### Cache Not Updating

```bash
# Manually refresh cache
python3 ~/.cursor-governance/ops/scripts/pre_execution_checker.py
```

### Low Effectiveness Rate

```bash
# Check lesson effectiveness
python3 ~/.cursor-governance/ops/scripts/prevention_effectiveness_tracker.py --calculate

# Review ineffective lessons (< 50% effectiveness)
cat ~/.cursor-governance/ops/logs/effectiveness_metrics.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('\n'.join([f\"{k}: {v:.1f}%\" for k,v in d['lesson_effectiveness'].items() if v < 50]))"
```

## Success Metrics

- **Prevention Rate:** >= 95%
- **Mistake Repetition Rate:** < 5%
- **Lesson Effectiveness:** >= 80%
- **Component Health:** >= 90%
- **Auto-Apply Rate:** >= 50%

## Related Documentation

- `setup-new-workspace.md` - Workspace setup guide
- `formal_lesson_extractor.py` - Formal lesson extraction
- `repeated-mistakes.md` - Mistake database

