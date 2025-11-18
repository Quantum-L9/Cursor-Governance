---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "LRN-002"
component_name: "Quick Fix Patterns Database"
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
integrates_with: ["INT-SSP-001", "LRN-001"]
api_endpoints: []
data_sources: ["error_patterns", "solution_database", "user_feedback"]
outputs: ["quick_fixes", "pattern_recognition", "instant_solutions"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Document proven quick solutions for common problems to accelerate problem resolution"
summary: "Instant solutions database with proven quick fixes, pattern recognition, and diagnostic commands for common development issues"
business_value: "Reduces problem resolution time from hours to seconds through proven quick fix patterns"
success_metrics: ["fix_success_rate >= 0.95", "time_to_resolution <= 60s", "pattern_recognition_accuracy >= 0.90"]

# === INTEGRATION METADATA ===
suite_2_origin: "quick-fixes.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive quick fix pattern database"

# === TAGS & CLASSIFICATION ===
tags: ["learning", "quick-fixes", "solutions", "patterns", "troubleshooting"]
keywords: ["quick", "fix", "solution", "pattern", "instant", "troubleshooting"]
related_components: ["INT-SSP-001", "LRN-001"]
startup_required: true
mode_type: "learning"
---

# Quick Fix Patterns Database
**Created:** 2025-01-29T16:00:00Z  
**Purpose:** Document proven quick solutions for common problems

---

## ⚡ **INSTANT SOLUTIONS**

### **JSON Parsing Issues**
**Problem:** JSON wrapped in string
**Quick Fix:** Double `json.loads()`
**Time:** 2 seconds
**Code:**
```python
if isinstance(content, str) and content.startswith('"'):
    parsed = json.loads(json.loads(content))
```

### **Supabase Authentication**
**Problem:** Manual headers not working
**Quick Fix:** Use credential type
**Time:** 2 minutes
**Config:**
```json
{
  "authentication": "predefinedCredentialType",
  "nodeCredentialType": "supabaseApi"
}
```

### **Missing Node IDs in n8n**
**Problem:** Workflow import fails due to missing IDs
**Quick Fix:** Add `"id": "nodeName"` to nodes
**Time:** 30 seconds per node

### **Expression Syntax Errors**
**Problem:** Spaces in expressions break n8n
**Quick Fix:** Remove spaces
**Time:** 1 second
**Before:** `{{ $vars.KEY }}`
**After:** `{{$vars.KEY}}`

### **Wrong n8n URL**
**Problem:** Using wrong instance URL
**Quick Fix:** Check Configuration/.env
**Time:** 10 seconds
**Command:** `grep "N8N_BASE_URL" Configuration/.env`

### **User Wants Folder Access**
**Problem:** User says "display folder in sidebar/left margin"
**Quick Fix:** Symlink to workspace, don't create docs
**Time:** 5 seconds
**Command:** `ln -s /path/to/folder /workspace/.folder-name`
**Rule:** "Display in sidebar" = symlink, not documentation

---

## 🎯 **PATTERN RECOGNITION**

### **When You See These Errors:**
- `Invalid character in header content` → Use credential type
- `JSONDecodeError` → Check for string wrapping
- `Workflow import failed` → Check for missing node IDs
- `Authentication failed` → Check credential method
- `Expression error` → Remove spaces from expressions

### **Quick Diagnostic Commands:**
```bash
# Check JSON format
file yourfile.json

# Check n8n credentials
grep "N8N_" Configuration/.env

# Validate workflow
bash scripts/validate-n8n-headers.sh workflow.json
```

---

**Last Updated:** 2025-11-18T00:00:00Z  
**Success Rate:** 95% when applied correctly
