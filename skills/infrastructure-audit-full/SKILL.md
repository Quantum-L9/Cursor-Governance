---
name: infrastructure-audit-full
description: 🔍 Complete System Audit
disable-model-invocation: true
---

---
command: AUDIT_FULL
version: 1.0.0
category: infrastructure
tags: [audit, quality, production-readiness, validation]
dependencies: []
risk_level: safe
requires_backup: false
estimated_duration: 3-5min
---

# 🔍 Complete System Audit

## 📖 Purpose
Comprehensive pre-launch audit checking workflows, credentials, configuration, documentation, and production readiness.

## 🎪 When to Use
- Before production deployments
- Weekly/monthly system checks
- After major changes
- Client demonstrations
- Pre-launch checklist

## 🚀 Execution

**Audits:**
1. All workflow files (valid JSON, no errors)
2. Credentials (all configured, no placeholders)
3. Configuration files (complete, no TODOs)
4. Documentation (present and current)
5. Backups (recent and valid)
6. Error handling (present in workflows)
7. Security (no exposed secrets)

**Output:**
```
🔍 Complete System Audit

✅ Workflows: 12/12 valid
✅ Credentials: 7/7 configured
✅ Configuration: Complete
✅ Documentation: 95% coverage
✅ Backups: Current (2 days ago)
✅ Error Handling: Implemented
✅ Security: No issues

Production Readiness: 9.2/10 (EXCELLENT)
Blockers: 0
Recommendations: 3 (optional)

Status: ✅ READY FOR DEPLOYMENT
```

## ✅ Success Metrics
- ✅ Zero critical issues
- ✅ All workflows valid
- ✅ Production-ready confirmed

---

*Command Standard Version: 2.0.0*

