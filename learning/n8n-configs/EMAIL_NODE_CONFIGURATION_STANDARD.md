---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "LRN-007"
component_name: "Email Node Configuration Standard"
layer: "intelligence"
domain: "learning"
type: "learning"
status: "active"
created: "2025-10-13T00:00:00Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: []
integrates_with: ["LRN-001", "LRN-002"]
api_endpoints: []
data_sources: ["n8n_email_configs", "workflow_patterns"]
outputs: ["configuration_standards", "fix_guides"]

# === OPERATIONAL METADATA ===
execution_mode: "reference"
monitoring_required: false
logging_level: "info"
performance_tier: "reference"

# === BUSINESS METADATA ===
purpose: "Standardize email node configuration across all n8n workflows to ensure consistency and prevent configuration errors"
summary: "Learning database documenting standard email node configuration patterns, correct parameter usage, and common mistakes to avoid"
business_value: "Ensures consistent email node configuration reducing configuration errors and improving maintainability"
success_metrics: ["configuration_consistency >= 0.95", "error_reduction >= 0.90", "standardization_rate >= 0.95"]

# === INTEGRATION METADATA ===
suite_2_origin: "EMAIL_NODE_CONFIGURATION_STANDARD.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive email node configuration standards"

# === TAGS & CLASSIFICATION ===
tags: ["learning", "n8n", "email", "configuration", "standard"]
keywords: ["email", "n8n", "configuration", "standard", "smtp", "node"]
related_components: ["LRN-001", "LRN-002"]
startup_required: false
mode_type: "learning"
---

# Email Node Configuration Standard

## ✅ CORRECT Configuration (Use This)

### Standard Email Send Node Configuration
```json
{
  "parameters": {
    "fromEmail": "={{$vars.SMTP_USER_LOGISTICS}}",
    "toEmail": "={{$json.to}}",
    "subject": "={{$json.subject}}",
    "emailFormat": "html",
    "html": "={{$json.body}}",
    "options": {
      "allowUnauthorizedCerts": false
    }
  },
  "credentials": {
    "smtp": {
      "id": "smtp-linda-logistics2",
      "name": "Gmail - Linda - Logistics2"
    }
  },
  "type": "n8n-nodes-base.emailSend",
  "typeVersion": 2.1
}
```

## 🔑 Key Configuration Points

### 1. From Email
- ✅ **USE:** `"fromEmail": "={{$vars.SMTP_USER_LOGISTICS}}"`
- ❌ **DON'T USE:** 
  - `"fromEmail": "={{$vars.SMTP_USER}}"` (wrong variable)
  - `"fromEmail": "noreply@scrapmanagement.com"` (hardcoded)

### 2. Email Format
- ✅ **USE:** `"emailFormat": "html"`
- ✅ **USE:** `"html": "={{$json.body}}"` (or appropriate content field)
- ❌ **DON'T USE:**
  - `"text": "={{$json.body}}"` (plain text)
  - `"message": "={{$json.body}}"` (old parameter)

### 3. Credentials
- ✅ **USE:** 
  ```json
  "credentials": {
    "smtp": {
      "id": "smtp-linda-logistics2",
      "name": "Gmail - Linda - Logistics2"
    }
  }
  ```
- ❌ **DON'T USE:**
  - Different credential IDs
  - `nodeCredentialType` or `authentication` parameters

### 4. Type Version
- ✅ **USE:** `"typeVersion": 2.1`
- ❌ **DON'T USE:** `"typeVersion": 2` or older versions

## 📋 Quick Reference - Parameter Names

| Parameter | Value Template | Description |
|-----------|---------------|-------------|
| `fromEmail` | `={{$vars.SMTP_USER_LOGISTICS}}` | Sender email from env var |
| `toEmail` | `={{$json.to}}` | Recipient (dynamic) |
| `subject` | `={{$json.subject}}` | Email subject (dynamic) |
| `emailFormat` | `html` | Always use HTML format |
| `html` | `={{$json.body}}` | Email content (HTML) |
| `options.allowUnauthorizedCerts` | `false` | Security setting |

## 🔄 How to Fix Existing Email Nodes

### Search and Replace Pattern

**OLD Pattern 1 (text):**
```json
"fromEmail": "={{$vars.SMTP_USER}}",
"toEmail": "={{$json.to}}",
"subject": "={{$json.subject}}",
"text": "={{$json.body}}"
```

**NEW Pattern:**
```json
"fromEmail": "={{$vars.SMTP_USER_LOGISTICS}}",
"toEmail": "={{$json.to}}",
"subject": "={{$json.subject}}",
"emailFormat": "html",
"html": "={{$json.body}}"
```

**OLD Pattern 2 (message):**
```json
"fromEmail": "noreply@scrapmanagement.com",
"toEmail": "={{$vars.ERROR_HANDLER_ESCALATION_EMAIL}}",
"subject": "Error Alert",
"message": "Error details..."
```

**NEW Pattern:**
```json
"fromEmail": "={{$vars.SMTP_USER_LOGISTICS}}",
"toEmail": "={{$vars.ERROR_HANDLER_ESCALATION_EMAIL}}",
"subject": "Error Alert",
"emailFormat": "html",
"html": "Error details..."
```

## ✏️ Step-by-Step Fix Guide

1. **Find the email node** in your workflow JSON
2. **Update fromEmail:**
   - Change `$vars.SMTP_USER` → `$vars.SMTP_USER_LOGISTICS`
   - Change hardcoded emails → `$vars.SMTP_USER_LOGISTICS`
3. **Add emailFormat:**
   - Add `"emailFormat": "html"` parameter
4. **Update content field:**
   - Change `"text"` → `"html"`
   - Change `"message"` → `"html"`
5. **Verify credentials:**
   - Ensure credential ID is `smtp-linda-logistics2`
   - Ensure credential name is `Gmail - Linda - Logistics2`
6. **Check typeVersion:**
   - Update to `2.1` if different

## 📁 Files Updated (Reference)

### ✅ Already Updated (Use as examples)
- `Master_Agent/Sub_Agents/01_Freight_Rate_Request/03_Freight_Rate_Request_Agent_v1.5.json`
  - Send RFQ Email (line ~128)
  - Send Decision Email (line ~681)
  - Send No Quotes Email (line ~785)
- `Master_Agent/Sub_Agents/00_Centralized_Services/03_Rate_Limiting_Service.json`
  - Email Rate Limit Alert (line ~208)
- `Master_Agent/Sub_Agents/00_Centralized_Services/02_Health_Check_System.json`
  - Email Health Alert (line ~208)
- `Master_Agent/Sub_Agents/00_Centralized_Services/01_Centralized_Error_Handler.json`
  - Email Escalation (line ~216)

## 🔍 How to Find Email Nodes

### Using grep:
```bash
grep -n "n8n-nodes-base.emailSend" *.json
```

### Using search in JSON:
Look for nodes with:
- `"type": "n8n-nodes-base.emailSend"`
- `"typeVersion": 2` or `2.1`

## ⚠️ Common Mistakes to Avoid

1. ❌ Using `text` instead of `html` + `emailFormat`
2. ❌ Using wrong environment variable (`SMTP_USER` instead of `SMTP_USER_LOGISTICS`)
3. ❌ Hardcoding email addresses instead of using variables
4. ❌ Missing `emailFormat: "html"` parameter
5. ❌ Using old credential configurations
6. ❌ Not updating typeVersion to 2.1

## 🎯 Why These Changes?

1. **HTML Format:** Better email rendering, supports formatting
2. **Correct Variable:** `SMTP_USER_LOGISTICS` is the proper configured variable
3. **Standardization:** Consistent configuration across all workflows
4. **Maintainability:** Easy to update all workflows from one place
5. **Best Practices:** Follows n8n 2.1 email node standards

## 📝 Environment Variables Required

Ensure these are set in n8n:
- `SMTP_USER_LOGISTICS` - logistics2@scrapmanagement.com (or configured email)

Optional recipients (workflow-specific):
- `ERROR_HANDLER_ESCALATION_EMAIL`
- `HEALTH_CHECK_ALERT_EMAIL`
- `REVOPS_EMAIL`

---

**Last Updated:** 2025-10-13  
**Standard Version:** 1.0  
**Applies To:** All Linda Logistics workflows
