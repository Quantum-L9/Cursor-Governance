---
name: analysis-performance-profile
description: ⚡ Performance Profile - System Performance Analysis
disable-model-invocation: true
---

---
command: PERFORMANCE_PROFILE
version: 1.0.0
category: analysis
tags: [performance, profiling, benchmarking, optimization, metrics]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: 1-2min
---

# ⚡ Performance Profile - System Performance Analysis

## 📖 Purpose
Analyze system performance, identify bottlenecks, measure execution times, and provide optimization recommendations. Essential for maintaining fast, efficient automations.

## 🎪 When to Use
- **After deployment** - Benchmark new workflows
- **Performance degradation** - Identify what slowed down
- **Regular optimization** - Monthly performance review
- **Capacity planning** - Understand system limits
- **Cost optimization** - Find expensive operations

## 🚀 Execution

### 📊 Performance Metrics Collected

#### 1. Workflow Execution Times (30 sec)
```yaml
For each workflow:
  - Average execution time
  - Min/max execution time
  - 95th percentile (P95)
  - 99th percentile (P99)
  - Execution count (24h)
  - Trend analysis (faster/slower)
```

#### 2. Webhook Response Times (20 sec)
```yaml
For each webhook:
  - Average response time
  - Min/max response
  - Timeout rate
  - Success rate
  - Geographic latency (if applicable)
```

#### 3. Database Performance [[memory:2516763]] (15 sec)
```sql
Supabase Metrics:
  - Query execution times
  - Connection pool usage
  - Slow query identification
  - Index usage analysis
  - Table scan detection
```

#### 4. API Call Performance (15 sec)
```yaml
External API Latency:
  OpenAI:
    - Avg latency: [X]ms
    - Success rate: [X]%
    - Token usage: [X] tokens/day
    
  Anthropic:
    - Avg latency: [X]ms
    - Success rate: [X]%
    - Token usage: [X] tokens/day
    
  Twilio:
    - Avg latency: [X]ms
    - Success rate: [X]%
    - Message count: [X]/day
```

#### 5. Bottleneck Detection (20 sec)
```yaml
Identifies:
  - Slowest workflows
  - Slowest nodes within workflows
  - High-latency API calls
  - Database query bottlenecks
  - Memory-intensive operations
```

---

## 📊 Performance Report Output

```markdown
# ⚡ Performance Profile Report

**Date:** 2025-10-01 16:15:00  
**Period:** Last 24 hours  
**Executions Analyzed:** 1,247  
**Overall Performance:** ✅ EXCELLENT

---

## Executive Summary

**System Performance Score: 92/100** ✅

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Avg Workflow Time | 1.9s | <5s | ✅ Excellent |
| Avg Webhook Response | 142ms | <500ms | ✅ Excellent |
| Database Latency | 23ms | <100ms | ✅ Excellent |
| API Success Rate | 98.5% | >95% | ✅ Excellent |
| Timeout Rate | 0.3% | <1% | ✅ Excellent |

---

## Workflow Performance Analysis

### Fast Workflows (✅ <2s avg)

| Workflow | Avg Time | Min | Max | P95 | Executions |
|----------|----------|-----|-----|-----|------------|
| Communication | 0.8s | 0.5s | 1.2s | 1.0s | 456 |
| Buyer Matching | 1.2s | 0.8s | 2.1s | 1.8s | 234 |
| Lead Qualification | 1.8s | 1.2s | 3.4s | 2.8s | 189 |

### Moderate Workflows (⚠️ 2-4s avg)

| Workflow | Avg Time | Min | Max | P95 | Executions |
|----------|----------|-----|-----|-----|------------|
| Material Classification | 2.3s | 1.5s | 4.8s | 3.9s | 167 |
| RevOps Automation | 3.1s | 2.1s | 6.2s | 5.1s | 145 |

### Slow Workflows (🔴 >4s avg)

*None detected* ✅

---

## Bottleneck Analysis

### Top 5 Performance Bottlenecks

#### 1. 🔴 VanillaSoft API Calls (2.5s avg)
**Impact:** HIGH  
**Affected Workflows:** Lead Qualification, RevOps  
**Frequency:** 189 calls/day  
**Issue:** External API latency outside our control

**Recommendations:**
- ✅ Implement caching (reduce calls by 40%)
- ✅ Add timeout (prevent hanging)
- ✅ Use async processing (don't block workflow)
- ✅ Consider queueing for batch processing

**Potential Savings:** 472s/day → 1.3 hours/day

---

#### 2. 🟡 OpenAI GPT-4o Calls (850ms avg)
**Impact:** MEDIUM  
**Affected Workflows:** Material Classification, QA  
**Frequency:** 312 calls/day  
**Cost:** ~$15/day

**Recommendations:**
- ✅ Cache common classifications (50% hit rate possible)
- ✅ Use batch API for non-urgent requests
- ✅ Consider smaller model for simple tasks
- ⚡ Implement result caching in Supabase

**Potential Savings:** 133s/day + $7.50/day cost reduction

---

#### 3. 🟢 Database Joins on Large Tables (180ms avg)
**Impact:** LOW  
**Affected Workflows:** Buyer Matching  
**Frequency:** 234 calls/day  
**Issue:** Full table scans on buyers table

**Recommendations:**
- ✅ Add index on material_type column
- ✅ Add index on location column
- ✅ Consider materialized views for common queries
- ⚡ Optimize query structure

**Potential Savings:** 42s/day

---

#### 4. 🟢 Supabase Logging Writes (45ms avg)
**Impact:** LOW  
**Affected Workflows:** All workflows  
**Frequency:** 1,247 calls/day

**Recommendations:**
- ✅ Use async/background logging
- ✅ Batch log entries every 10 seconds
- ⚡ Consider using queues for logs

**Potential Savings:** 56s/day

---

#### 5. 🟢 ElevenLabs Voice Synthesis (420ms avg)
**Impact:** LOW  
**Affected Workflows:** Voice agents  
**Frequency:** 89 calls/day

**Recommendations:**
- ✅ Pre-generate common phrases
- ✅ Cache synthesized audio
- ⚡ Use streaming for long texts

**Potential Savings:** 37s/day

---

## API Performance Breakdown

### OpenAI API
```yaml
Metrics:
  Avg Latency: 850ms
  Success Rate: 99.2%
  Failed Requests: 2 (0.8%)
  Timeout Rate: 0.3%
  
Usage:
  Total Calls: 312/day
  Total Tokens: 245,000/day
  Estimated Cost: ~$15/day
  
Performance Trend: ↗️ +15ms vs last week (seasonal variation)
```

### Anthropic API
```yaml
Metrics:
  Avg Latency: 720ms
  Success Rate: 99.5%
  Failed Requests: 1 (0.5%)
  Timeout Rate: 0%
  
Usage:
  Total Calls: 67/day
  Total Tokens: 89,000/day
  Estimated Cost: ~$8/day
  
Performance Trend: → Stable
```

### Supabase Database
```yaml
Metrics:
  Avg Query Time: 23ms
  Slow Queries (>100ms): 12 (1%)
  Connection Pool: 5/10 used (healthy)
  Failed Queries: 0
  
Top Slow Queries:
  1. Buyer matching query: 180ms (needs index)
  2. Lead history query: 125ms (acceptable)
  3. Material search: 98ms (acceptable)
```

### Twilio WhatsApp
```yaml
Metrics:
  Avg Latency: 256ms
  Success Rate: 100%
  Failed Messages: 0
  
Usage:
  Messages Sent: 45/day
  Estimated Cost: ~$0.45/day
  
Performance Trend: → Stable
```

---

## Webhook Response Times

| Endpoint | Avg | Min | Max | P95 | Status |
|----------|-----|-----|-----|-----|--------|
| /lead-qualification | 145ms | 98ms | 312ms | 245ms | ✅ |
| /material-classification | 198ms | 132ms | 456ms | 367ms | ✅ |
| /buyer-matching | 167ms | 112ms | 289ms | 234ms | ✅ |
| /revops-automation | 134ms | 89ms | 278ms | 212ms | ✅ |
| /communication | 138ms | 95ms | 245ms | 198ms | ✅ |

**Analysis:** All webhooks responding well below 500ms target ✅

---

## Resource Utilization

### n8n Instance
```yaml
CPU: 12% avg (peak: 34%)
Memory: 340MB / 1GB (34%)
Disk I/O: Low
Network: 2.3 MB/hour

Status: ✅ Plenty of headroom for growth
Capacity: Can handle 5-10x current load
```

### Supabase
```yaml
Storage: 245MB / 500MB (49%)
API Requests: 3,245/day (well within limits)
Database Connections: 5/10 active
Bandwidth: 1.2 GB/month

Status: ✅ Efficient usage
Capacity: Can scale to 3-4x current load
```

---

## Performance Trends (7 Days)

```
Avg Workflow Execution Time:
  Week Ago: 1.8s
  Today:    1.9s
  Change:   +0.1s (+5.5%)
  
Trend: ↗️ Slight increase (acceptable, within normal variation)
```

```
Avg Webhook Response:
  Week Ago: 138ms
  Today:    142ms
  Change:   +4ms (+2.9%)
  
Trend: → Stable
```

```
Error Rate:
  Week Ago: 1.8%
  Today:    1.5%
  Change:   -0.3% (-16.7%)
  
Trend: ↘️ Improving ✅
```

---

## Optimization Recommendations

### High Impact (Do This Week)

1. **Cache VanillaSoft Responses** ⚡
   - Impact: -472s/day execution time
   - Effort: 2 hours
   - ROI: High

2. **Add Database Indexes** ⚡
   - Impact: -42s/day query time
   - Effort: 30 minutes
   - ROI: High

3. **Cache OpenAI Classifications** ⚡
   - Impact: -133s/day + $7.50/day savings
   - Effort: 3 hours
   - ROI: Very High

### Medium Impact (This Month)

4. **Batch Supabase Logging**
   - Impact: -56s/day
   - Effort: 2 hours
   - ROI: Medium

5. **Optimize Material Classification**
   - Impact: -0.5s avg per execution
   - Effort: 4 hours
   - ROI: Medium

### Low Impact (Backlog)

6. **Pre-generate Voice Phrases**
7. **Implement Query Result Caching**
8. **Add CDN for Static Assets**

---

## Cost Analysis

### Current Daily Costs
```yaml
OpenAI API:      $15.00/day
Anthropic API:   $8.00/day
Twilio WhatsApp: $0.45/day
Vapi Voice:      $2.40/day (30min @ $0.08/min)
ElevenLabs:      $0.80/day
n8n Instance:    $0.00 (included in plan)
Supabase:        $0.00 (within free tier)

Total: ~$26.65/day (~$800/month)
```

### Optimization Potential
```yaml
OpenAI Caching:    -$7.50/day
Batch Processing:  -$2.00/day
Voice Caching:     -$0.60/day

Potential Savings: ~$10/day (~$300/month)
New Total: ~$16.65/day (~$500/month)
```

---

## Next Steps

### Immediate (Today)
```bash
@think "implement VanillaSoft caching"
@think "add database indexes for buyer matching"
```

### This Week
```bash
@think "implement OpenAI classification caching"
@performance-profile  # Re-measure after optimizations
```

### This Month
```bash
@think "batch Supabase logging implementation"
@think "optimize material classification workflow"
```

---

**Performance Profile:** COMPLETE ✅  
**Overall Assessment:** EXCELLENT PERFORMANCE  
**Action Required:** Implement 3 high-impact optimizations  
**Potential Improvement:** 37% faster + 38% cost reduction

---

*Performance Profile v1.0.0 - Fast Systems, Happy Users*
```

---

## 🔗 Combines Well With

### Optimization Workflow
```bash
1. @performance-profile          # Identify bottlenecks
2. @think "optimize X"           # Implement fixes
3. @test-workflows               # Verify no regressions
4. @performance-profile          # Measure improvement
```

### Regular Monitoring
```bash
# Monthly
@performance-profile
→ Document trends
→ Plan optimizations
→ Update capacity estimates
```

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial performance profiling command

---

*Command Standard Version: 2.0.0*
*Measure, Optimize, Repeat*

