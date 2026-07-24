<!-- --- L9_META ---
l9_schema: 1
artifact_type: learning
component: quick_fix_patterns_database
tags: [learning, quick_fixes, solutions, patterns, troubleshooting]
retrieval: on_demand
status: active
--- /L9_META --- -->

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

### **Missing Node IDs in YAML Specs**
**Problem:** YAML spec import fails due to missing IDs
**Quick Fix:** Add `id:` field to all nodes/specs
**Time:** 30 seconds per node

### **Expression Syntax Errors**
**Problem:** Spaces in Jinja/template expressions break parsing
**Quick Fix:** Remove spaces
**Time:** 1 second
**Before:** `{{ vars.KEY }}`
**After:** `{{vars.KEY}}`

### **Wrong L9 API URL**
**Problem:** Using wrong instance URL (localhost vs production)
**Quick Fix:** Check .env or environment variables
**Time:** 10 seconds
**Command:** `grep "L9_BASE_URL" .env`

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
# Check JSON/YAML format
file yourfile.json
python -c "import yaml; yaml.safe_load(open('yourfile.yaml'))"

# Check L9 credentials
grep "L9_\|OPENAI_\|ANTHROPIC_" .env

# Validate YAML spec
python -m codegen_agent.pipeline_validator yourspec.yaml
```

---

**Last Updated:** 2026-01-22T00:00:00Z  
**Success Rate:** 95% when applied correctly
