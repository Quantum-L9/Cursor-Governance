---
name: infrastructure-security-audit
description: 🔒 Security Audit - Comprehensive Security Scanning
disable-model-invocation: true
---

---
command: SECURITY_AUDIT
version: 1.0.0
category: infrastructure
tags: [security, audit, credentials, vulnerabilities, compliance]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: 2-3min
---

# 🔒 Security Audit - Comprehensive Security Scanning

## 📖 Purpose
Scan codebase for security vulnerabilities, exposed credentials, hardcoded secrets, and compliance issues. Essential pre-deployment check for enterprise systems.

## 🎪 When to Use
- **Before deployment** - Always run before pushing to production
- **Weekly maintenance** - Regular security posture check
- **After code changes** - Verify no security regressions
- **Compliance audits** - Document security status
- **Onboarding new code** - Scan third-party integrations

## 🚀 Execution

### 🔍 Security Scan Areas

#### 1. Credential Exposure (CRITICAL)
```bash
Scanning for:
  ❌ Hardcoded API keys
  ❌ Exposed passwords
  ❌ OAuth tokens in code
  ❌ Database credentials
  ❌ Private keys
  ❌ Webhook secrets

Patterns Checked:
  - API_KEY = "..."
  - password: "..."
  - sk-... (OpenAI keys)
  - xoxb-... (Slack tokens)
  - postgresql://user:pass@...
```

#### 2. Environment Variable Usage [[memory:3496356]]
```bash
Validating:
  ✅ All credentials use {{$env.VAR}}
  ✅ No placeholder values (YOUR_API_KEY)
  ✅ .env template exists
  ✅ .env in .gitignore
  ✅ Credentials documented
```

#### 3. Code Injection Vectors
```bash
Checking for:
  ❌ SQL injection risks
  ❌ Command injection
  ❌ XSS vulnerabilities
  ❌ Unsafe eval() usage
  ❌ Unvalidated input
```

#### 4. n8n Workflow Security
```bash
Workflow checks:
  ✅ Webhook authentication enabled
  ✅ No exposed endpoints without auth
  ✅ Rate limiting configured
  ✅ Input validation present
  ✅ Error messages don't expose secrets
```

#### 5. Enterprise Compliance [[memory:2510896]]
```bash
Standards verification:
  ✅ Error handling comprehensive
  ✅ Logging sanitized (no secrets in logs)
  ✅ WhatsApp alerts configured (+1-980-266-9595)
  ✅ Audit trail enabled (Supabase)
  ✅ Encryption for sensitive data
```

---

## 📊 Output Format

```markdown
# 🔒 Security Audit Report
**Date:** YYYY-MM-DD HH:MM:SS
**System:** Sales Agent Production

## Risk Summary
| Severity | Count | Status |
|----------|-------|--------|
| 🔴 Critical | 0 | ✅ SAFE |
| 🟡 High | 0 | ✅ SAFE |
| 🟠 Medium | 2 | ⚠️ REVIEW |
| 🟢 Low | 5 | ℹ️ OPTIONAL |

## Security Score: 92/100 (EXCELLENT)

---

## 🔴 Critical Issues (MUST FIX)
*None found* ✅

---

## 🟡 High Priority Issues (FIX SOON)
*None found* ✅

---

## 🟠 Medium Priority Issues (REVIEW)

### 1. Rate Limiting Not Configured
**File:** workflow_x.json
**Issue:** Webhook lacks rate limiting
**Risk:** Potential DoS or cost overrun
**Fix:** Add rate limit: 100 req/min

### 2. Missing Input Validation
**File:** workflow_y.json
**Issue:** User input not validated
**Risk:** Injection attacks possible
**Fix:** Add validation node before processing

---

## 🟢 Low Priority Issues (NICE TO HAVE)

1. Consider adding request ID tracking
2. Update error messages (less verbose)
3. Add HTTPS enforcement headers
4. Implement API key rotation schedule
5. Consider adding honeypot endpoints

---

## ✅ Security Strengths

- ✅ No exposed credentials detected
- ✅ Environment variables properly used
- ✅ Error handling comprehensive
- ✅ Logging properly sanitized
- ✅ Webhook authentication enabled
- ✅ Audit trail active (Supabase)

---

## 📋 Recommendations

### Immediate Actions
1. Add rate limiting to 2 webhook endpoints
2. Add input validation to user-facing workflows

### Short Term (This Week)
3. Implement request ID tracking
4. Update verbose error messages
5. Document credential rotation process

### Long Term (This Month)
6. Set up automated security scanning
7. Implement honeypot monitoring
8. Add penetration testing schedule

---

## 🎯 Compliance Status

**Enterprise Standards [[memory:2510896]]:**
- ✅ Bulletproof error handling
- ✅ Comprehensive logging (Supabase)
- ✅ No hardcoded credentials
- ✅ WhatsApp error alerts configured
- ✅ Modular architecture maintained

**Overall Status:** PRODUCTION SAFE ✅

---

**Next Security Audit:** 1 week
**Auditor:** SECURITY_AUDIT v1.0.0
```

---

## 🔗 Combines Well With

### Before Security Audit
- Make code changes
- Update workflows
- Add new integrations

### After Security Audit
- **@credentials-manage** - Fix credential issues
- **@workflow-validate** - Fix workflow issues
- **@backup-versioned** - Safe to backup
- **@deploy-production** - Safe to deploy

---

## 📝 Version History
- **1.0.0** (2025-10-01): Initial security audit command for Sales Agent

---

*Command Standard Version: 2.0.0*
*Security First - Deploy with Confidence*

