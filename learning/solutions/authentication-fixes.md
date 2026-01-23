---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "LRN-004"
component_name: "Authentication Solutions Database"
layer: "intelligence"
domain: "learning"
type: "learning"
status: "active"
created: "2025-01-29T16:00:00Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: []
integrates_with: ["LRN-001", "LRN-002", "SEC-003"]
api_endpoints: []
data_sources: ["authentication_failures", "credential_patterns"]
outputs: ["solution_documentation", "prevention_rules"]

# === OPERATIONAL METADATA ===
execution_mode: "reference"
monitoring_required: false
logging_level: "info"
performance_tier: "reference"

# === BUSINESS METADATA ===
purpose: "Prevent repeated authentication failures through documented solutions and prevention rules"
summary: "Learning database documenting authentication solutions, particularly Supabase authentication methods, to prevent repeated failures"
business_value: "Prevents repeated authentication failures reducing debugging time from 45+ minutes to 2 minutes"
success_metrics: ["failure_prevention_rate >= 0.95", "solution_effectiveness = 1.0", "time_savings >= 0.95"]

# === INTEGRATION METADATA ===
suite_2_origin: "authentication-fixes.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive authentication solution documentation"

# === TAGS & CLASSIFICATION ===
tags: ["learning", "authentication", "supabase", "credentials", "security"]
keywords: ["authentication", "supabase", "credentials", "auth", "predefinedCredentialType", "supabaseApi"]
related_components: ["LRN-001", "LRN-002", "SEC-003"]
startup_required: false
mode_type: "learning"
---

# Authentication Solutions Database
**Created:** 2025-01-29T16:00:00Z  
**Purpose:** Prevent repeated authentication failures

---

## 🚨 **CRITICAL: Supabase Authentication Method**

### **Problem Description**
- Manual apikey/Authorization headers causing authentication failures
- Multiple failed attempts over hours
- Wrong authentication method being used repeatedly

### **Failed Approaches**
```json
// WRONG - Manual headers (DOESN'T WORK)
"headerParameters": {
  "parameters": [
    {
      "name": "apikey",
      "value": "={{$vars.SUPABASE_SERVICE_ROLE_KEY}}"
    },
    {
      "name": "Authorization", 
      "value": "Bearer {{$vars.SUPABASE_SERVICE_ROLE_KEY}}"
    }
  ]
}
```

### **Working Solution**
```python
# CORRECT - Use Supabase client with proper authentication
from supabase import create_client

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]  # Service key for server-side ops
)
```

### **Key Insight**
- **NEVER** use manual headers for Supabase
- **ALWAYS** use the official Supabase client library
- **NEVER** assume manual headers will work

### **Prevention**
- **ALWAYS** check credential template first
- **ALWAYS** use `predefinedCredentialType` + `supabaseApi`
- **NEVER** add manual apikey/Authorization headers

### **Search Tags**
`supabase`, `auth`, `credentials`, `headers`, `predefinedCredentialType`, `supabaseApi`

### **Time Impact**
- **Without Solution:** 45+ minutes of failed attempts
- **With Solution:** 2 minutes
- **User Frustration:** HIGH → ZERO

---

## 🔧 **Common Authentication Issues & Solutions**

### **Issue: Wrong L9 API URL**
**Solution:** Always read from .env
```bash
grep "L9_BASE_URL" .env
# Must be: https://l9.igorbeylin.com for production
```

### **Issue: Expression Syntax Errors**
**Solution:** Use correct syntax without spaces
```json
// WRONG
"{{ $vars.KEY }}"

// CORRECT  
"{{$vars.KEY}}"
```

### **Issue: Missing API Keys**
**Solution:** Check L9 VPS .env file
```bash
# On VPS
ssh admin@157.180.73.53 "grep 'MCP_API_KEY\|SUPABASE' /opt/l9/.env"

# Local
grep "MCP_API_KEY\|L9_" .env
```

---

## 🔐 **L9 VPS Authentication**

### **Primary Method: cursor_memory_client.py**
```bash
python3 agents/cursor/cursor_memory_client.py health  # Check auth
python3 agents/cursor/cursor_memory_client.py search "query"  # Uses MCP_API_KEY_C
```

### **API Keys**
| Key | Purpose | Location |
|-----|---------|----------|
| `MCP_API_KEY_C` | Cursor agent auth | VPS .env |
| `MCP_API_KEY_L` | L-CTO agent auth | VPS .env |

### **Never Use**
- ~~n8n predefinedCredentialType~~ (deprecated)
- ~~Manual Authorization headers~~ (use client library)
- ~~Local Docker for production~~ (VPS only)

---

**Last Updated:** 2026-01-20T16:00:00Z  
**Success Rate:** 100% when applied correctly
