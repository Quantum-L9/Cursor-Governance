---
name: pipelines-check
description: 🔍 CHECK - Weekly System Health & Maintenance
disable-model-invocation: true
---

---
command: CHECK
version: 1.0.0
category: pipeline
tags: [pipeline, maintenance, health, weekly, monitoring]
dependencies: [health-check, security-audit, performance-profile, backup-versioned, cleanup-workspace, archive-legacy, node-update]
risk_level: safe
requires_backup: true
estimated_duration: 8-10min
---

# 🔍 CHECK - Weekly System Health & Maintenance

## 📖 Purpose
**Your weekly maintenance pipeline.** Comprehensive system health check, cleanup, optimization, and preventive maintenance. Run every Sunday to keep your system healthy and efficient.

## 🎪 When to Use
- **Weekly maintenance** - Every Sunday morning
- **Before major releases** - Baseline system health
- **After incidents** - Verify system recovered
- **Monthly deep clean** - Comprehensive maintenance

## 🚀 Execution - 7 Steps (8-10 min)

---

### Step 1: Current Health Status (1 min)
**Command:** `@health-check`

**Checks:**
- n8n instance status
- Workflow activity
- Supabase connection
- Webhook endpoints
- Integration services
- Recent errors

**Baseline Metrics:**
```yaml
Current State:
  - Active workflows: X
  - Success rate: X%
  - Error rate: X%
  - Avg response time: Xms
  - Resource usage: X%
```

---

### Step 2: Security Audit (2-3 min)
**Command:** `@security-audit`

**Scans:**
- Exposed credentials
- Hardcoded secrets
- Security vulnerabilities
- Compliance status
- Authentication issues

**Output:**
```yaml
Security Status:
  Critical: 0 ✅
  High: 0 ✅
  Medium: X ⚠️
  Low: X ℹ️
  
  Overall: PRODUCTION SAFE
```

---

### Step 3: Performance Analysis (1-2 min)
**Command:** `@performance-profile`

**Analyzes:**
- Workflow execution times
- API latencies
- Database performance
- Bottlenecks
- Cost analysis
- Optimization opportunities

**Output:**
```yaml
Performance:
  Score: XX/100
  Bottlenecks: X found
  Optimization potential: X%
  Cost savings: $X/month
```

---

### Step 4: Weekly Backup (1 min)
**Command:** `@backup-versioned --weekly`

**Creates:**
- Timestamped weekly backup
- Backup manifest
- Retention: Keep 4 weeks
- Auto-cleanup old backups

**Output:**
```
✅ Backup: backup_weekly_20251001.tar.gz
📦 Retained: 4 weeks of backups
🗑️ Cleaned: 2 old backups
```

---

### Step 5: Workspace Cleanup (1-2 min)
**Command:** `@cleanup-workspace`

**Cleans:**
- Temporary files
- Old logs
- Test data
- Cache files
- .DS_Store files
- _CLEAN workflow copies

**Output:**
```
🧹 Cleaned 47 temporary files
💾 Freed 12.4 MB disk space
✅ Workspace optimized
```

---

### Step 6: Archive Old Files (1 min)
**Command:** `@archive-legacy`

**Archives:**
- Files >30 days old
- Superseded versions
- Deprecated code
- Old documentation

**Output:**
```
📦 Archived 8 legacy files
📁 Archive: Archive/20251001_weekly_archive/
✅ Workspace decluttered
```

---

### Step 7: Update Check (1-2 min)
**Command:** `@node-update`

**Checks:**
- Deprecated n8n nodes
- Node version updates
- Breaking changes
- Security patches
- Feature updates

**Output:**
```yaml
Node Status:
  Deprecated: 0 ✅
  Updates Available: 3 ℹ️
  Breaking Changes: 0 ✅
  
  Status: UP TO DATE
```

---

## ✅ CHECK Report Output

```markdown
# 🔍 Weekly CHECK Report

**Date:** 2025-10-06 09:00:00 (Sunday)  
**Check Duration:** 9m 15s  
**Overall Status:** ✅ HEALTHY

---

## Executive Summary

**System Health Score: 94/100** 💚

### Health Assessment
✅ **n8n Instance:** HEALTHY (all workflows active)  
✅ **Security:** EXCELLENT (no critical issues)  
✅ **Performance:** VERY GOOD (slight optimization potential)  
✅ **Backups:** CURRENT (4 weeks retention)  
✅ **Workspace:** CLEAN (47 temp files removed)  
✅ **Updates:** CURRENT (no deprecated nodes)

### Week Summary
- **Executions:** 8,734 total
- **Success Rate:** 98.2% (excellent)
- **Avg Response:** 145ms (excellent)
- **Errors:** 157 (1.8% rate - excellent)
- **Deployments:** 2 (both successful)

---

## Detailed Results

### 1. Health Status ✅

| Component | Status | Latency | Details |
|-----------|--------|---------|---------|
| n8n Instance | ✅ UP | 42ms | 9 workflows active |
| Supabase DB | ✅ UP | 21ms | Optimal performance |
| Webhooks | ✅ UP | 145ms | All responding |
| OpenAI API | ✅ UP | 820ms | Normal latency |
| Anthropic API | ✅ UP | 695ms | Normal latency |
| Twilio WhatsApp | ✅ UP | 245ms | Messaging active |
| Vapi Voice | ✅ UP | 165ms | Voice calls ready |
| VanillaSoft CRM | ⚠️ SLOW | 2.8s | Elevated (monitor) |

**Overall:** 8/8 services operational (1 slow)

---

### 2. Security Audit ✅

**Security Score: 92/100** (Excellent)

| Severity | This Week | Last Week | Change |
|----------|-----------|-----------|--------|
| Critical | 0 | 0 | → |
| High | 0 | 0 | → |
| Medium | 2 | 3 | ↓ -1 |
| Low | 5 | 5 | → |

**Improvements This Week:**
- ✅ Fixed rate limiting on buyer-matching webhook
- ✅ No new vulnerabilities introduced

**Outstanding Items:**
- ⚠️ Add input validation to revops workflow
- ℹ️ 5 low-priority items (documented)

---

### 3. Performance Profile ⚡

**Performance Score: 89/100** (Very Good)

#### Workflow Performance
| Workflow | Avg Time | vs Last Week | Status |
|----------|----------|--------------|--------|
| Communication | 0.8s | +0.1s | ✅ |
| Buyer Matching | 1.3s | -0.1s | ✅ Improving |
| Lead Qualification | 1.9s | +0.1s | ✅ |
| Material Classification | 2.4s | +0.1s | ⚠️ Slight increase |
| RevOps Automation | 3.2s | +0.1s | ⚠️ Slight increase |

**Trend:** Slightly slower (+0.1s avg) - within normal variation

#### Top Bottlenecks
1. **VanillaSoft API** (2.8s avg) - Slow this week
2. **OpenAI Calls** (820ms avg) - Normal
3. **Database Joins** (180ms avg) - Needs indexing

**Optimization Potential:**
- Implement VanillaSoft caching → Save 450s/day
- Add database indexes → Save 40s/day
- Cache OpenAI results → Save $8/day

---

### 4. Backup Status ✅

**Backup Health: EXCELLENT**

| Backup Type | Last Created | Size | Status |
|-------------|--------------|------|--------|
| Weekly | Today, 9:00 AM | 2.8 MB | ✅ Current |
| Pre-Deploy | 2 days ago | 2.7 MB | ✅ Current |
| Emergency | 5 days ago | 2.6 MB | ✅ Available |

**Retention:**
- ✅ 4 weekly backups kept
- ✅ 2 old backups cleaned up
- ✅ Total backup storage: 11.2 MB (optimal)

---

### 5. Workspace Cleanup ✅

**Cleanup Results:**
```
Files Cleaned:
  - 23 temporary test files
  - 12 _CLEAN workflow copies
  - 8 .DS_Store files
  - 4 log files
  
Space Freed: 12.4 MB
Status: WORKSPACE OPTIMIZED ✅
```

---

### 6. Archive Status ✅

**Archiving Results:**
```
Archived This Week:
  - 5 superseded workflow versions
  - 3 old documentation files
  
Archive Location: Archive/20251006_weekly_archive/
Total Archived Files: 8
Status: DECLUTTERED ✅
```

---

### 7. Node Updates ✅

**Update Status:**

| Status | Count | Action Required |
|--------|-------|-----------------|
| Deprecated Nodes | 0 | ✅ None |
| Updates Available | 3 | ℹ️ Optional |
| Breaking Changes | 0 | ✅ None |
| Security Patches | 0 | ✅ None |

**Available Updates:**
1. HTTP Request node: v4.2 → v4.3 (minor improvements)
2. Supabase node: v1.0 → v1.1 (new features)
3. Code node: v2.0 → v2.1 (bug fixes)

**Recommendation:** Updates are optional, no urgency

---

## Action Items

### 🔥 High Priority (This Week)
1. ⚠️ Monitor VanillaSoft CRM latency
2. ⚠️ Add input validation to revops workflow

### 📋 Medium Priority (This Month)
3. 💡 Implement VanillaSoft caching (saves 450s/day)
4. 💡 Add database indexes (saves 40s/day)
5. 💡 Update 3 optional node versions

### 💡 Low Priority (Backlog)
6. Consider OpenAI result caching
7. Review 5 low-priority security items
8. Set up performance dashboard

---

## Week-Over-Week Comparison

| Metric | Last Week | This Week | Change |
|--------|-----------|-----------|--------|
| Executions | 8,234 | 8,734 | +500 ↗️ +6% |
| Success Rate | 97.8% | 98.2% | +0.4% ↗️ |
| Avg Response | 140ms | 145ms | +5ms ↗️ +3.6% |
| Error Rate | 2.2% | 1.8% | -0.4% ↘️ |
| Deployments | 3 | 2 | -1 |
| Security Score | 91/100 | 92/100 | +1 ↗️ |

**Trend:** System health improving, load increasing (good sign!)

---

## Overall Assessment

**Status:** ✅ SYSTEM HEALTHY AND OPTIMIZED

**Summary:**
- All critical systems operational
- Security posture excellent
- Performance very good
- Backups current
- Workspace clean
- No urgent issues

**Recommendation:** Continue normal operations, implement optimizations this week

---

**Next CHECK:** Next Sunday (October 13, 2025)  
**Frequency:** Weekly maintenance

---

*Checked by CHECK Pipeline v1.0.0*
*Prevention > Reaction*
```

---

## 🔗 Workflow Integration

### Weekly Routine
```bash
# Every Sunday morning
Pipeline: CHECK
  → Review report
  → Address action items
  → Plan week's optimizations
```

### Before Major Release
```bash
Pipeline: CHECK          # Baseline current state
→ Pipeline: BUILD        # Build release features
→ Pipeline: SHIP         # Deploy to production
→ Pipeline: CHECK        # Verify post-release
```

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial CHECK pipeline for weekly maintenance

---

*Command Standard Version: 2.0.0*
*Preventive Maintenance - System Longevity*

