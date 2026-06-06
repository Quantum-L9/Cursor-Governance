---
name: infrastructure-health-check
description: 💚 Health Check - System Status Verification
disable-model-invocation: true
---

---
command: HEALTH_CHECK
version: 1.0.0
category: infrastructure
tags: [health, monitoring, status, verification, diagnostics]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: 30-60sec
---

# 💚 Health Check - System Status Verification

## 📖 Purpose
Quick system health verification. Check all critical services, connections, and workflows in under 60 seconds. Your daily "is everything working?" command.

## 🎪 When to Use
- **Daily morning check** - Verify system health before work
- **Post-deployment** - Confirm deployment success
- **Before major changes** - Baseline current state
- **Troubleshooting** - Quick diagnostic
- **Status updates** - Quick system overview

## 🚀 Execution

### ⚡ Quick Health Check (30-60 sec)

#### 1. n8n Instance Status (10 sec)
```yaml
Check: https://ibeylin.app.n8n.cloud
  ✅ Instance reachable
  ✅ API responding
  ✅ Authentication working
  ✅ Workflows accessible
  ✅ Executions viewable

Status Codes:
  200 OK → ✅ HEALTHY
  401 Unauthorized → ❌ Auth issue
  503 Unavailable → ❌ Instance down
  Timeout → ❌ Network issue
```

#### 2. Workflow Status (10 sec)
```yaml
Active Workflows:
  ✅ Lead Qualification (Active, last run: 2min ago)
  ✅ Material Classification (Active, last run: 5min ago)
  ✅ Buyer Matching (Active, last run: 3min ago)
  ✅ RevOps Automation (Active, last run: 15min ago)
  ✅ Communication (Active, last run: 1min ago)
  
  Total: 9 workflows
  Active: 9 (100%)
  Errors: 0
  Paused: 0
```

#### 3. Supabase Connection [[memory:2516763]] (5 sec)
```sql
Check: Supabase connectivity
  ✅ Connection successful
  ✅ Database responding (<50ms)
  ✅ Tables accessible
  ✅ Logging working
  
Test Query: SELECT 1;
Result: ✅ 1
Latency: 23ms
```

#### 4. Webhook Endpoints (15 sec)
```bash
Test: GET requests to webhook URLs
  ✅ /webhook/lead-qualification → 200 OK (145ms)
  ✅ /webhook/material-classification → 200 OK (132ms)
  ✅ /webhook/buyer-matching → 200 OK (156ms)
  ✅ /webhook/revops-automation → 200 OK (141ms)
  ✅ /webhook/communication → 200 OK (138ms)
  
  Success: 5/5 (100%)
  Avg Response: 142ms (excellent)
```

#### 5. Integration Services (10 sec)
```yaml
External Services:
  ✅ OpenAI API (gpt-4o available)
  ✅ Anthropic API (claude-3-5-sonnet available)
  ✅ Twilio WhatsApp (+1-980-266-9595 active)
  ✅ Vapi Voice (API responding)
  ✅ ElevenLabs (Voice synthesis available)
  ⚠️ VanillaSoft CRM (slow response - 2.5s)
  
  Status: 6/6 reachable (1 slow)
```

#### 6. Recent Errors (5 sec)
```sql
Check: Last 100 executions
  Errors: 2 (2% error rate) ✅
  Success: 98 (98% success rate) ✅
  
  Recent Errors:
    - VanillaSoft timeout (1x, 15min ago)
    - Invalid material format (1x, 45min ago)
  
  Status: ✅ HEALTHY (error rate <5%)
```

---

## 📊 Health Report Output

```markdown
# 💚 System Health Report

**Time:** 2025-10-01 16:00:00  
**Check Duration:** 47 seconds  
**Overall Status:** ✅ HEALTHY

---

## System Status: ✅ ALL SYSTEMS OPERATIONAL

| Component | Status | Latency | Details |
|-----------|--------|---------|---------|
| n8n Instance | ✅ UP | 45ms | 9 workflows active |
| Supabase DB | ✅ UP | 23ms | All tables accessible |
| Webhooks | ✅ UP | 142ms avg | 5/5 responding |
| OpenAI API | ✅ UP | 215ms | gpt-4o ready |
| Anthropic API | ✅ UP | 189ms | claude ready |
| Twilio WhatsApp | ✅ UP | 256ms | +1-980-266-9595 |
| Vapi Voice | ✅ UP | 178ms | API active |
| ElevenLabs | ✅ UP | 167ms | Synthesis ready |
| VanillaSoft CRM | ⚠️ SLOW | 2.5s | Elevated latency |

---

## Workflow Health (9 Total)

### ✅ Active & Healthy (9)
1. **Lead Qualification Enhanced v3.0**
   - Status: Active ✅
   - Last Execution: 2min ago
   - Success Rate: 99.2% (last 100)
   - Avg Duration: 1.8s

2. **Material Classification Advanced v3.0**
   - Status: Active ✅
   - Last Execution: 5min ago
   - Success Rate: 98.5% (last 100)
   - Avg Duration: 2.3s

3. **Buyer Matching Enhanced v3.0**
   - Status: Active ✅
   - Last Execution: 3min ago
   - Success Rate: 100% (last 100)
   - Avg Duration: 1.2s

4. **RevOps Automation Complete v3.0**
   - Status: Active ✅
   - Last Execution: 15min ago
   - Success Rate: 97.8% (last 100)
   - Avg Duration: 3.1s

5. **Quality Assurance Enterprise v3.0**
   - Status: Active ✅
   - Last Execution: 8min ago
   - Success Rate: 99.5% (last 100)
   - Avg Duration: 1.5s

*...and 4 more workflows (all healthy)*

### ⚠️ Warnings (1)
- **VanillaSoft Integration:** Slow API responses (2.5s vs normal 500ms)
  - Impact: Workflows may take longer
  - Action: Monitor, contact VanillaSoft if persists

### ❌ Critical Issues (0)
*None detected* ✅

---

## Performance Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Workflow Success Rate | 98% | >95% | ✅ Excellent |
| Avg Response Time | 142ms | <500ms | ✅ Excellent |
| Database Latency | 23ms | <100ms | ✅ Excellent |
| Error Rate | 2% | <5% | ✅ Excellent |
| Active Workflows | 9/9 | 100% | ✅ Perfect |
| Failed Executions (24h) | 12 | <50 | ✅ Good |

---

## Recent Activity (Last Hour)

- **Executions:** 156 total
- **Success:** 153 (98%)
- **Errors:** 3 (2%)
  - VanillaSoft timeout: 1x
  - Invalid input format: 2x
- **Avg Duration:** 1.9s
- **Longest:** 3.1s (RevOps workflow)
- **Shortest:** 0.8s (Communication workflow)

---

## System Resources

**n8n Instance:**
- CPU: 12% (normal)
- Memory: 340MB / 1GB (34%)
- Active Connections: 23
- Queue Size: 0 (no backlog)

**Supabase:**
- Active Connections: 5/10
- Query Performance: Excellent
- Storage: 245MB / 500MB (49%)
- API Requests (24h): 3,245

---

## Recommendations

### ✅ All Clear
System is operating normally. No immediate action required.

### 📊 Monitoring
- ✅ Continue monitoring VanillaSoft latency
- ✅ Review 3 recent errors (low priority)

### 🎯 Optional Optimizations
- Consider caching VanillaSoft responses
- Add retry logic for invalid input errors

---

## Next Steps

```bash
# If all healthy (current status):
✅ Continue normal operations
✅ Check again tomorrow morning

# If issues detected:
@think "investigate [specific issue]"
@performance-profile  # For latency issues
@security-audit       # For security concerns
```

---

**Health Check:** COMPLETE ✅  
**Overall Status:** HEALTHY 💚  
**Confidence:** HIGH  
**Next Check:** Tomorrow morning or post-deployment

---

*Health Check v1.0.0 - System Operating Normally*
```

---

## 🚦 Status Levels

```yaml
✅ HEALTHY (90-100%):
  All systems operational
  Performance excellent
  No action required
  
⚠️ WARNING (70-89%):
  Some issues detected
  System functional but degraded
  Monitor closely
  Consider investigation
  
❌ CRITICAL (<70%):
  Major issues detected
  System functionality impaired
  Immediate action required
  Run diagnostics
```

---

## 🔗 Combines Well With

### Daily Routine
```bash
# Morning
@health-check  # Quick 30-second status

# After deployment
@workflow-deploy
@health-check  # Verify deployment
```

### Troubleshooting Flow
```bash
@health-check                    # Identify issues
@think "investigate X issue"     # Deep dive
@performance-profile             # If performance issue
@security-audit                  # If security concern
@health-check                    # Verify fix
```

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial health check command

---

*Command Standard Version: 2.0.0*
*Quick Check - Peace of Mind*

