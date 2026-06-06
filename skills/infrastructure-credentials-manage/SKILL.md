---
name: infrastructure-credentials-manage
description: 🔑 Credentials Management
disable-model-invocation: true
---

---
command: CREDENTIALS_MANAGE
version: 1.1.0
category: infrastructure
tags: [credentials, security, validation, api-keys]
dependencies: []
risk_level: moderate
requires_backup: false
estimated_duration: 30-60sec
---

# 🔑 Credentials Management

## 📖 Purpose
Validate and manage API credentials and environment variables. Ensure all required credentials exist with proper permissions and no placeholders.

## 🎪 When to Use
- Before deployments
- After credential rotation
- Weekly security checks
- New workflow integration
- Environment setup

## 🚀 Execution

**Validates:**
1. All credential references in workflows
2. Credentials exist in target environment
3. No placeholder values (API_KEY_HERE, etc.)
4. Proper permissions configured
5. Production vs dev credentials

**Checks:**
- Supabase API keys
- Twilio credentials
- OpenAI API keys
- WhatsApp tokens
- Custom API credentials

**Output:**
```
🔑 Credentials Validation

Required Credentials: 7
✅ supabase_api_key (valid, proper permissions)
✅ openai_api_key (valid)
✅ twilio_account_sid (valid)
✅ twilio_auth_token (valid)
✅ whatsapp_business_token (valid)
✅ google_maps_api_key (valid)
✅ sendgrid_api_key (valid)

Status: ALL CREDENTIALS VALID
No placeholders detected
Production environment: CONFIRMED
```

## ✅ Success Metrics
- ✅ All credentials validated
- ✅ Zero placeholders
- ✅ Proper environment confirmed

---

*Command Standard Version: 2.0.0*

