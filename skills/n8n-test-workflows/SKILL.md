---
name: n8n-test-workflows
description: 🧪 Test Workflows - Comprehensive Workflow Testing
disable-model-invocation: true
---

---
command: TEST_WORKFLOWS
version: 1.0.0
category: n8n
tags: [testing, validation, workflows, qa, integration]
dependencies: [workflow-validate]
risk_level: safe
requires_backup: false
estimated_duration: 2-3min
---

# 🧪 Test Workflows - Comprehensive Workflow Testing

## 📖 Purpose
Test n8n workflows before deployment. Validates webhooks, database connections, API integrations, error handling, and end-to-end flows. Essential quality gate before production.

## 🎪 When to Use
- **Before deployment** - Always test before @workflow-deploy
- **After modifications** - Verify changes don't break functionality
- **Integration testing** - Test multi-workflow interactions
- **Regression testing** - Ensure old features still work

## 🚀 Execution

### Test Suite Overview
```
Test Categories:
  1. Structural Tests (validation)
  2. Webhook Tests (connectivity)
  3. Database Tests (Supabase)
  4. Integration Tests (APIs)
  5. Error Handling Tests
  6. End-to-End Tests
```

---

### 1. Structural Tests (30 sec)
```yaml
Validates:
  ✅ JSON structure valid
  ✅ All nodes configured
  ✅ No missing parameters
  ✅ Expressions syntactically correct
  ✅ Connections properly defined

Tool: @workflow-validate
```

---

### 2. Webhook Tests (45 sec)
```bash
For each webhook workflow:
  Test: POST to webhook URL
  Payload: Test data matching schema
  Expected: 200 OK response
  Verify: Workflow triggered
  Check: Execution completed successfully

Webhook Endpoints:
  - https://ibeylin.app.n8n.cloud/webhook/lead-qualification
  - https://ibeylin.app.n8n.cloud/webhook/material-classification
  - https://ibeylin.app.n8n.cloud/webhook/buyer-matching
  - https://ibeylin.app.n8n.cloud/webhook/revops-automation
```

**Test Example:**
```bash
curl -X POST https://ibeylin.app.n8n.cloud/webhook/lead-qualification \
  -H "Content-Type: application/json" \
  -d '{
    "contact_name": "Test Buyer",
    "company": "Test Company",
    "material_type": "HDPE",
    "volume": "1000"
  }'

Expected: 
  Status: 200 OK
  Response: {"status": "success", "lead_id": "..."}
  Execution: Completed in n8n
```

---

### 3. Database Tests [[memory:2516763]] (30 sec)
```sql
Supabase Connection Tests:
  ✅ Connection successful
  ✅ Tables accessible
  ✅ INSERT operations work
  ✅ SELECT queries return data
  ✅ Logging tables writable

Test Queries:
  - SELECT 1; (connectivity)
  - INSERT INTO test_log (...) (write access)
  - SELECT * FROM leads LIMIT 1; (read access)
  - DELETE FROM test_log WHERE test=true; (cleanup)
```

---

### 4. Integration Tests (45 sec)
```yaml
External API Tests:
  OpenAI/Anthropic:
    ✅ API key valid
    ✅ Model accessible
    ✅ Test completion request
    
  VanillaSoft CRM:
    ✅ API connection works
    ✅ Can create test lead
    ✅ Can query leads
    
  Communication Services:
    ✅ Twilio WhatsApp reachable
    ✅ Can send test message
    ✅ Delivery confirmed
    
  Voice Agents (Vapi/ElevenLabs):
    ✅ API keys valid
    ✅ Service accessible
    ✅ Can create test call
```

---

### 5. Error Handling Tests [[memory:2510896]] (30 sec)
```yaml
Test Error Scenarios:
  Invalid Input:
    ✅ Workflow handles gracefully
    ✅ Error logged to Supabase
    ✅ User-friendly error returned
    ✅ No workflow crash
    
  Missing Data:
    ✅ Workflow continues or fails gracefully
    ✅ Error notification sent (WhatsApp)
    ✅ Retry logic works if configured
    
  API Failures:
    ✅ Fallback to alternative provider
    ✅ Error logged properly
    ✅ User notified appropriately
    
  Rate Limit Hit:
    ✅ Workflow pauses/retries
    ✅ Does not spam API
    ✅ Error handled correctly
```

---

### 6. End-to-End Tests (30 sec)
```yaml
Complete Flow Tests:
  Lead Qualification Flow:
    1. Webhook receives lead
    2. Lead validated and scored
    3. Data logged to Supabase
    4. Notification sent
    ✅ Complete flow works

  Material Classification Flow:
    1. Material data received
    2. AI classification performed
    3. Results logged
    4. Buyer matching triggered
    ✅ Complete flow works

  Buyer Matching Flow:
    1. Material classified
    2. Buyers queried from DB
    3. Matching algorithm runs
    4. Results returned
    ✅ Complete flow works
```

---

## 📊 Test Report Output

```markdown
# 🧪 Workflow Test Report

**Date:** 2025-10-01 15:45:00
**Workflows Tested:** 9
**Test Duration:** 2m 45s

## Test Summary

| Category | Passed | Failed | Skipped |
|----------|--------|--------|---------|
| Structural | 9 | 0 | 0 |
| Webhooks | 7 | 0 | 2 |
| Database | 9 | 0 | 0 |
| Integrations | 8 | 1 | 1 |
| Error Handling | 9 | 0 | 0 |
| End-to-End | 6 | 0 | 3 |
| **TOTAL** | **48** | **1** | **6** |

## Overall Status: ✅ PASS (98% success rate)

---

## ✅ Passed Tests (48)

### Structural Tests (9/9)
- ✅ lead_qualification_enhanced_v3.0.json
- ✅ material_classification_advanced_v3.0.json
- ✅ buyer_matching_enhanced_v3.0.json
- ✅ revops_automation_complete_v3.0.json
- ✅ quality_assurance_enterprise_v3.0.json
- ✅ communication_multichannel_v3.0.json
- ✅ agent_mac_multichannel_reply_flow_v3.0.json
- ✅ mac_multichannel_reply_flow_v3.0.json
- ✅ material_classification_enhanced_v3.0.json

### Webhook Tests (7/7 active)
- ✅ /webhook/lead-qualification → 200 OK (145ms)
- ✅ /webhook/material-classification → 200 OK (198ms)
- ✅ /webhook/buyer-matching → 200 OK (167ms)
- ✅ /webhook/revops-automation → 200 OK (134ms)
- ✅ /webhook/communication → 200 OK (156ms)
- ✅ /webhook/agent-mac → 200 OK (142ms)
- ✅ /webhook/quality-assurance → 200 OK (151ms)

*2 workflows don't have webhooks (scheduled triggers)*

### Database Tests (9/9)
- ✅ Supabase connection successful
- ✅ All tables accessible
- ✅ Write operations work
- ✅ Read operations work
- ✅ Query performance acceptable (<200ms)
- ✅ Logging tables writable
- ✅ Test data inserted successfully
- ✅ Test data retrieved successfully
- ✅ Test data cleaned up

### Integration Tests (8/9)
- ✅ OpenAI API → Connected (gpt-4o available)
- ✅ Anthropic API → Connected (claude-3-5-sonnet available)
- ✅ Supabase → Connected (all tables accessible)
- ✅ Twilio WhatsApp → Connected (test message sent)
- ✅ Vapi Voice → Connected (API key valid)
- ✅ ElevenLabs → Connected (voice synthesis available)
- ✅ n8n Instance → Connected (workflows accessible)
- ❌ VanillaSoft CRM → Connection timeout (see issues below)
- ⚪ Retell Voice → Skipped (not configured)

### Error Handling Tests (9/9)
- ✅ Invalid input handled gracefully
- ✅ Missing data doesn't crash workflow
- ✅ API failures trigger fallback
- ✅ Errors logged to Supabase
- ✅ WhatsApp notifications sent (+1-980-266-9595)
- ✅ User-friendly error messages
- ✅ No sensitive data in errors
- ✅ Retry logic works correctly
- ✅ Rate limiting respected

### End-to-End Tests (6/6 active)
- ✅ Lead Qualification → Material Classification → Complete
- ✅ Material Classification → Buyer Matching → Complete
- ✅ Buyer Matching → Communication → Complete
- ✅ RevOps Automation → Complete flow
- ✅ Quality Assurance → Complete flow
- ✅ Multi-channel Communication → Complete flow

*3 workflows pending implementation (skipped)*

---

## ❌ Failed Tests (1)

### Integration Test Failed: VanillaSoft CRM
**Error:** Connection timeout after 30 seconds
**Impact:** CRM integration workflows may fail
**Workflow Affected:** lead_qualification_enhanced_v3.0.json
**Severity:** 🟡 Medium (workflow has fallback)

**Recommended Action:**
1. Check VanillaSoft API status
2. Verify API key is valid
3. Check network connectivity
4. Test API endpoint manually:
   ```bash
   curl -H "Authorization: Bearer $VANILLASOFT_API_KEY" \
     https://api.vanillasoft.com/v1/health
   ```
5. If issue persists, use fallback workflow without CRM

**Fallback:** Workflow logs to Supabase only (no CRM sync)

---

## ⚪ Skipped Tests (6)

1. **Webhook: scheduled_report_generation** - No webhook (scheduled trigger)
2. **Webhook: weekly_cleanup** - No webhook (scheduled trigger)
3. **Integration: Retell Voice** - Not configured yet
4. **E2E: RevOps Dashboard** - Dashboard not implemented
5. **E2E: Quality Scoring** - Agent not complete
6. **E2E: Communication Multi-channel** - Voice agents not deployed

---

## 📊 Performance Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Avg Response Time | 157ms | ✅ Excellent (<200ms) |
| Slowest Webhook | 198ms | ✅ Good (<500ms) |
| Database Query Time | 45ms avg | ✅ Excellent (<100ms) |
| Workflow Success Rate | 98% | ✅ Excellent (>95%) |
| Error Rate | 2% | ✅ Excellent (<5%) |

---

## 🎯 Deployment Recommendation

**Status:** ✅ **SAFE TO DEPLOY**

**Confidence:** HIGH (98% test pass rate)

**Conditions:**
- ✅ All structural tests pass
- ✅ All webhooks responding
- ✅ Database connectivity confirmed
- ✅ Error handling verified
- ⚠️ One integration issue (VanillaSoft) - has fallback

**Next Steps:**
1. ✅ Proceed with @workflow-deploy
2. ⚠️ Monitor VanillaSoft connection
3. ✅ Run @health-check post-deployment
4. ✅ Review first 10 executions

---

**Test Suite:** TEST_WORKFLOWS v1.0.0
**Execution ID:** test_20251001_154500
```

---

## 🔗 Combines Well With

### Standard Testing Flow
```bash
1. @workflow-validate     # Structural validation
2. @test-workflows        # Comprehensive testing
3. @backup-versioned      # Safety backup
4. @workflow-deploy       # Deploy if tests pass
```

### CI/CD Integration
```bash
# Automated testing pipeline
@test-workflows --ci-mode --fail-fast
# Fails immediately on first error
# Returns exit code for automation
```

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial workflow testing command

---

*Command Standard Version: 2.0.0*
*Test First - Deploy with Confidence*

