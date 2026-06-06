---
name: pipelines-rapid-analysis
description: ⚡ Rapid Analysis Pipeline
disable-model-invocation: true
---

---
command: RAPID_ANALYSIS
version: 1.0.0
category: pipeline
tags: [pipeline, analysis, quick, health-check, status]
dependencies: [workspace-scan, dependency-map, performance-profile, security-audit, audit-full]
risk_level: safe
requires_backup: false
estimated_duration: 5-8min
---

# ⚡ Rapid Analysis Pipeline

## 📖 Purpose
Quick comprehensive analysis of current workspace state. Provides instant insight into system health, architecture, performance, security, and production readiness. Perfect for status checks, onboarding, or troubleshooting.

## 🎪 When to Use
- Quick system health check
- Onboarding new team members
- Before major changes or deployments
- After receiving system from another team
- Troubleshooting unknown issues
- Monthly system reviews
- Client demonstrations

## ⚠️ When NOT to Use
- When you need deep investigation (use individual commands)
- During active incidents (use @emergency-rollback)
- For specific targeted analysis (use specific tools)

## 🔍 Pre-Conditions
- [ ] Workspace accessible
- [ ] All workflow files present
- [ ] System in stable state (not during deployment)

## 🚀 Execution

This pipeline executes **5 parallel analysis steps** for speed:

---

### 📊 Pipeline Overview
```
Step 1: Workspace Structure Analysis
Step 2: Dependency & Architecture Mapping
Step 3: Performance Profiling (if available)
Step 4: Security Status Check
Step 5: Production Readiness Audit
```

**Note:** Steps 1-2 run in parallel, then 3-5 run in parallel for maximum speed.

---

### Step 1: Workspace Structure Analysis (1-2 min)
**Command:** `@workspace-scan`

**Purpose:** Understand current workspace organization and structure

**Analyzes:**
- Directory structure
- File organization
- Workflow count and distribution
- Documentation presence
- Script and configuration files
- Data files and backups

**Insights Generated:**
- Total workflows by category
- Code organization quality
- Missing documentation
- Redundant files
- Organizational improvements needed

**Success Criteria:**
- ✅ Complete directory scan
- ✅ All workflows identified
- ✅ Structure analysis complete
- ✅ Recommendations generated

**Output:**
```
📁 Workspace Structure
Total Files: 136
Workflows: 12 (organized)
Documentation: 15 files (good coverage)
Scripts: 8 (deployment & utilities)
Backups: 4 weekly backups (retention policy good)

Organization Score: 8.5/10 (Well organized)
Recommendations:
- Consider archiving 2 old backup files
- Add README to Testing/ folder
```

---

### Step 2: Dependency & Architecture Mapping (2-3 min)
**Command:** `@dependency-map`

**Purpose:** Visualize system architecture and dependencies

**Generates:**
- Complete dependency map
- Workflow relationship diagram
- Critical path identification
- Bottleneck detection
- Orphaned workflow identification

**Insights:**
- How many workflows
- How they connect
- Critical dependencies
- Single points of failure
- Circular dependencies (if any)

**Success Criteria:**
- ✅ All dependencies mapped
- ✅ Architecture visualized
- ✅ Critical paths identified
- ✅ Risks documented

**Output:**
```
🗺️ System Architecture
Workflows: 12
Dependencies: 27 connections
Critical Path: Linda Master Orchestrator → 5 sub-agents
Bottlenecks: 1 (Communication Manager - high traffic)
Single Points of Failure: 2
Circular Dependencies: 0

Complexity Score: 6.5/10 (Moderate)
Maintainability: 8.2/10 (Good)
```

---

### Step 3: Performance Profiling (1-2 min)
**Command:** `@performance-profile` (if implemented) or skip

**Purpose:** Analyze system performance metrics

**Monitors:**
- Workflow execution times
- Webhook response times
- Database query performance
- API call latencies
- Error rates
- Resource usage

**Metrics:**
- Average execution time
- Success rate
- Bottleneck identification
- Performance trends

**Success Criteria:**
- ✅ Key metrics collected
- ✅ Performance benchmarked
- ✅ Bottlenecks identified
- ✅ Trends analyzed

**Output:**
```
⚡ Performance Metrics
Avg Execution Time: 2.3s (good)
Success Rate: 99.4% (excellent)
Webhook Response: 148ms avg (excellent)
Database Queries: 1.9s avg (acceptable)
API Calls: 315ms avg (good)

Performance Score: 8.7/10 (Very Good)
Bottlenecks: None critical
Recommendations: Consider caching frequent DB queries
```

---

### Step 4: Security Status Check (2-3 min)
**Command:** `@security-audit`

**Purpose:** Quick security vulnerability scan

**Scans For:**
- Exposed credentials
- Hardcoded secrets
- Unsecured endpoints
- Injection vulnerabilities
- Missing authentication
- Insecure data handling

**Risk Levels:**
- 🔴 Critical (must fix immediately)
- 🟡 High (fix soon)
- 🟠 Medium (address in next sprint)
- 🟢 Low (nice to have)

**Success Criteria:**
- ✅ Complete security scan
- ✅ All vulnerabilities identified
- ✅ Risk levels assigned
- ✅ Remediation steps provided

**Output:**
```
🔒 Security Status
Critical Issues: 0
High Priority: 0
Medium Priority: 2
Low Priority: 5

Security Score: 8.1/10 (Good)

⚠️ Medium Priority Items:
1. Add rate limiting to 2 webhook endpoints
2. Implement request logging for audit trail

Overall: PRODUCTION SAFE (with recommendations)
```

---

### Step 5: Production Readiness Audit (1-2 min)
**Command:** `@audit-full`

**Purpose:** Comprehensive production readiness check

**Audits:**
- Workflow validity
- Configuration completeness
- Credential setup
- Error handling
- Documentation quality
- Backup status
- Monitoring setup

**Checklist:**
- ✅ All workflows valid
- ✅ No placeholder values
- ✅ Credentials configured
- ✅ Error handling present
- ✅ Documentation complete
- ✅ Backups current
- ✅ Monitoring active

**Success Criteria:**
- ✅ All critical items pass
- ✅ Production-ready confirmed
- ✅ Deployment blockers identified
- ✅ Recommendations documented

**Output:**
```
✅ Production Readiness
Status: READY FOR DEPLOYMENT

Critical Requirements: 12/12 ✅
- Workflows validated
- Credentials configured
- Error handling present
- Documentation complete
- Backups current
- Monitoring active

Readiness Score: 9.2/10 (Excellent)
Blockers: 0
Recommendations: 3 (all optional)
```

---

## ✅ Post-Conditions
- [ ] Complete system overview generated
- [ ] All health metrics collected
- [ ] Risks and issues identified
- [ ] Recommendations documented
- [ ] Analysis report created

## 🔗 Success Metrics
1. **Speed:** Analysis completed in < 8 minutes
2. **Completeness:** All 5 analysis steps executed
3. **Actionability:** Clear recommendations provided
4. **Clarity:** Report easy to understand

## 📊 Output Format

### Rapid Analysis Report
```markdown
# ⚡ Rapid Analysis Report
**Date:** 2025-10-01 15:30:00
**Duration:** 7 minutes 15 seconds
**System:** Linda Logistics Master Agent

---

## 🎯 Executive Summary

**Overall System Health: 8.5/10 (Very Good)**

✅ **Strengths:**
- Well-organized architecture (8.5/10)
- Excellent performance (8.7/10)
- Production-ready (9.2/10)
- Good documentation coverage

⚠️ **Areas for Improvement:**
- 2 medium-priority security items
- 1 bottleneck in Communication Manager
- Consider archiving old backups

🚫 **Critical Issues:** None

**Recommendation:** READY FOR PRODUCTION with minor improvements

---

## 📊 Detailed Analysis

### 1. Workspace Structure (8.5/10)
**Status:** ✅ Well Organized

| Metric | Count | Status |
|--------|-------|--------|
| Total Workflows | 12 | Good |
| Documentation Files | 15 | Excellent |
| Backup Files | 4 | Current |
| Scripts | 8 | Complete |

**Organization:**
- ✅ Clear folder structure
- ✅ Workflows categorized properly
- ✅ Documentation comprehensive
- ⚠️ 2 old backups could be archived

---

### 2. Architecture & Dependencies (7.5/10)
**Status:** ✅ Healthy Architecture

**System Composition:**
- Master Agents: 1
- Sub-Agents: 11
- Total Dependencies: 27 connections
- Critical Paths: 1 primary path

**Dependency Health:**
- ✅ No circular dependencies
- ✅ Clean integration patterns
- ⚠️ 1 bottleneck identified (Communication Manager)
- ⚠️ 2 single points of failure

**Architecture Diagram:**
```
Linda Master Orchestrator (CRITICAL)
├── Freight Rate Request
├── Dispatch Coordinator
│   ├── Trucker Selector
│   └── Load Assignment
└── Communication Manager (BOTTLENECK)
    ├── WhatsApp Handler
    ├── SMS Handler
    └── Email Handler
```

**Recommendations:**
- Add redundancy to Master Orchestrator
- Scale Communication Manager (high traffic)

---

### 3. Performance Metrics (8.7/10)
**Status:** ✅ Excellent Performance

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Avg Execution Time | 2.3s | <5s | ✅ Excellent |
| Success Rate | 99.4% | >99% | ✅ Excellent |
| Webhook Response | 148ms | <500ms | ✅ Excellent |
| Database Queries | 1.9s | <3s | ✅ Good |
| API Calls | 315ms | <1s | ✅ Excellent |
| Error Rate | 0.6% | <1% | ✅ Excellent |

**Trends:**
- 📈 Execution count: +12% this week
- 📉 Error rate: -0.2% (improving)
- 📊 Response time: Stable

**Bottlenecks:**
- Communication Manager: 150+ calls/hour (near capacity)

**Recommendations:**
- Implement caching for frequent DB queries (10-15% speedup)
- Monitor Communication Manager load (consider scaling)

---

### 4. Security Analysis (8.1/10)
**Status:** ✅ Production Safe

**Vulnerability Scan Results:**
| Severity | Count | Status |
|----------|-------|--------|
| Critical | 0 | ✅ None |
| High | 0 | ✅ None |
| Medium | 2 | ⚠️ Review |
| Low | 5 | ℹ️ Optional |

**Medium Priority Items:**
1. **Rate Limiting**
   - Issue: 2 webhook endpoints lack rate limiting
   - Risk: Potential DoS or cost overruns
   - Fix: Implement rate limits (100 req/min)

2. **Audit Logging**
   - Issue: No request logging for webhooks
   - Risk: Difficult to troubleshoot or audit
   - Fix: Add structured logging to Supabase

**Low Priority Items:**
- Add HTTPS enforcement headers
- Implement request ID tracking
- Consider API key rotation schedule
- Add input sanitization to 3 nodes
- Update error messages (less verbose)

**Overall:** No critical vulnerabilities, safe for production

---

### 5. Production Readiness (9.2/10)
**Status:** ✅ READY FOR DEPLOYMENT

**Checklist:**
✅ All 12 workflows validated
✅ Zero placeholder values
✅ All 7 credentials configured
✅ Error handling implemented
✅ Documentation 95% complete
✅ Backups current (last: 2 days ago)
✅ Monitoring active (Supabase logging)
✅ Rollback plan documented
✅ Team trained
✅ Change management approved

**Deployment Blockers:** 0

**Optional Improvements:**
- Add performance monitoring dashboard
- Implement automated testing
- Set up alerting thresholds

---

## 🎯 Action Items

### High Priority (This Week)
1. [ ] Implement rate limiting on 2 webhook endpoints
2. [ ] Add audit logging for webhook requests
3. [ ] Monitor Communication Manager load

### Medium Priority (This Sprint)
4. [ ] Implement DB query caching
5. [ ] Add redundancy to Master Orchestrator
6. [ ] Archive old backups (>1 month)

### Low Priority (Backlog)
7. [ ] Build performance dashboard
8. [ ] Implement automated testing
9. [ ] Set up alerting thresholds

---

## 📈 Key Metrics Summary

| Category | Score | Status |
|----------|-------|--------|
| Organization | 8.5/10 | ✅ Very Good |
| Architecture | 7.5/10 | ✅ Good |
| Performance | 8.7/10 | ✅ Excellent |
| Security | 8.1/10 | ✅ Good |
| Production Ready | 9.2/10 | ✅ Excellent |
| **Overall** | **8.5/10** | **✅ Very Good** |

---

## 💡 Quick Wins (< 1 hour)
1. Add rate limiting to webhooks (30 min)
2. Archive old backups (10 min)
3. Add logging to key workflows (20 min)

---

## 🚀 Deployment Recommendation

**Status:** ✅ APPROVED FOR PRODUCTION

**Confidence Level:** HIGH (8.5/10)

**Reasoning:**
- No critical issues detected
- All core requirements met
- Performance excellent
- Security acceptable
- Architecture sound

**Next Steps:**
1. Address 2 medium-priority security items (optional but recommended)
2. Run @deploy-production when ready
3. Monitor closely for first 24 hours

---

*Analysis completed by RAPID_ANALYSIS pipeline v1.0.0*
*Execution time: 7m 15s*
*Next analysis recommended: 1 week*
```

## 🔗 Combines Well With

### Before This Pipeline
- New project → **RAPID_ANALYSIS** (understand what you have)

### After This Pipeline
- **RAPID_ANALYSIS** → address issues → **@deploy-production**
- **RAPID_ANALYSIS** → weekly → **@weekly-maintenance**

## 💡 Pro Tips

### Tip 1: Run Weekly or Monthly
Keep regular pulse on system health.

### Tip 2: Perfect for Onboarding
Best way to understand new system quickly.

### Tip 3: Compare Reports Over Time
Track improvement trends.

### Tip 4: Share with Stakeholders
Executive summary is client-friendly.

### Tip 5: Before Major Changes
Baseline current state before big updates.

## 🔖 Examples

### Example 1: Quick Health Check
```
User: "@rapid-analysis on current system"
AI:
  ⚡ Running rapid analysis...
  
  [1/5] Workspace structure... ✅ DONE (1m 32s)
  [2/5] Architecture mapping... ✅ DONE (2m 15s)
  [3/5] Performance profiling... ✅ DONE (1m 48s)
  [4/5] Security scan... ✅ DONE (2m 22s)
  [5/5] Production readiness... ✅ DONE (1m 18s)
  
  ✅ ANALYSIS COMPLETE (7m 15s)
  
  📊 Overall Health: 8.5/10 (Very Good)
  ✅ Ready for production
  ⚠️ 2 minor improvements recommended
  
  Full report: reports/rapid_analysis_20251001.md
```

### Example 2: Pre-Deployment Check
```
User: "@rapid-analysis before deployment"
AI:
  [Running analysis...]
  
  ✅ COMPLETE (7m 15s)
  
  System Status: PRODUCTION READY
  Blockers: 0
  Recommendations: 3 (all optional)
  
  Proceed with deployment: YES
```

---

## 📚 Related Commands
- `workspace-scan` - Detailed structure analysis
- `dependency-map` - Architecture visualization
- `performance-profile` - Performance metrics
- `security-audit` - Security scanning
- `audit-full` - Production readiness
- `deploy-production` - Deploy after analysis

## 📝 Version History
- **1.0.0** (2025-10-01): Initial rapid analysis pipeline with 5-step comprehensive scan

---

*Command Standard Version: 2.0.0*
*Pipeline Type: Quick Analysis*
*Perfect For: Health checks, onboarding, pre-deployment*

