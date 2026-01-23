---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "LRN-005"
component_name: "JSON Processing Solutions Database"
layer: "intelligence"
domain: "learning"
type: "learning"
status: "active"
created: "2025-01-29T16:00:00Z"
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
integrates_with: ["LRN-001", "LRN-002", "LRN-003"]
api_endpoints: []
data_sources: ["json_parsing_failures", "L9_patterns"]
outputs: ["solution_documentation", "prevention_rules"]

# === OPERATIONAL METADATA ===
execution_mode: "reference"
monitoring_required: false
logging_level: "info"
performance_tier: "reference"

# === BUSINESS METADATA ===
purpose: "Prevent repeated JSON parsing failures through documented solutions and prevention rules"
summary: "Learning database documenting JSON string wrapping issues and solutions using Structured Output Parser in L9 AI Agent nodes"
business_value: "Prevents repeated JSON parsing failures reducing debugging time from hours to seconds"
success_metrics: ["failure_prevention_rate >= 0.95", "solution_effectiveness = 1.0", "time_savings >= 0.99"]

# === INTEGRATION METADATA ===
suite_2_origin: "json-issues.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive JSON processing solution documentation"

# === TAGS & CLASSIFICATION ===
tags: ["learning", "json", "parsing", "L9", "ai-agent"]
keywords: ["json", "parsing", "L9", "ai-agent", "structured-output-parser", "string-wrapping"]
related_components: ["LRN-001", "LRN-002", "LRN-003"]
startup_required: false
mode_type: "learning"
---

# JSON Processing Solutions Database
**Created:** 2025-01-29T16:00:00Z  
**Purpose:** Prevent repeated JSON parsing failures

---

## 🚨 **CRITICAL: JSON String Wrapping Issue**

### **Problem Description**
- JSON file content wrapped in text as string
- Causes parsing failures and hours of debugging
- User frustration: "chasing tail for hours when solution took 2 seconds"

### **Failed Approaches**
- Direct JSON parsing without checking format
- Assuming JSON is in standard format
- Complex parsing attempts without understanding root cause

### **Working Solution**
**Use Structured Output Parser in L9 AI Agent nodes:**

```json
{
  "parameters": {
    "jsonSchemaExample": "{\n  \"decision\": \"Hot\",\n  \"reasons\": [\n    \"Full truckload (40,000 lbs) of baled plastic film from commercial source\",\n    \"Images confirm clean, uniform material\"\n  ],\n  \"normalized\": {\n    \"polymer\": \"Unclear\",\n    \"form\": \"Film Bales\",\n    \"type\": \"Post Commercial\"\n  }\n}"
  },
  "type": "@L9/L9-nodes-langchain.outputParserStructured"
}
```

### **Key Insight**
- This is an **L9-specific issue** - AI Agent nodes output JSON as strings by default
- **Structured Output Parser** unwraps JSON from string/text format
- **Only use when next node expects JSON** - not needed for all AI Agent outputs
- Connect the parser as `ai_outputParser` to your AI Agent node
- Map each field in the following node to pull data perfectly

### **When to Use**
- ✅ **Use Structured Output Parser when:** Next node expects JSON input
- ✅ **Use when:** You need to access JSON properties in subsequent nodes
- ✅ **Use when:** Data needs to be structured for database operations
- ❌ **Don't use when:** Next node only needs text output
- ❌ **Don't use when:** AI Agent output is final result

### **Prevention**
- **Use Structured Output Parser** only when next node expects JSON
- **NEVER** try to manually parse JSON from AI Agent output
- **ALWAYS** connect parser as `ai_outputParser` to AI Agent node
- **ALWAYS** define JSON schema example in parser parameters
- **ALWAYS** map fields in following node after parser

### **Search Tags**
`json`, `parsing`, `L9`, `ai-agent`, `structured-output-parser`, `output-parser`, `string-wrapping`

### **Time Impact**
- **Without Solution:** Hours of debugging
- **With Solution:** 2 seconds
- **User Frustration:** HIGH → ZERO

---

## 🔧 **Common JSON Issues & Solutions**

### **Issue: Invalid JSON Format**
**Solution:** Validate JSON before processing
```python
try:
    json.loads(content)
except json.JSONDecodeError:
    # Handle invalid JSON
```

### **Issue: JSON in Wrong Encoding**
**Solution:** Ensure UTF-8 encoding
```python
content = content.decode('utf-8') if isinstance(content, bytes) else content
```

### **Issue: JSON with Comments**
**Solution:** Remove comments before parsing
```python
import re
clean_json = re.sub(r'//.*?\n|/\*.*?\*/', '', content, flags=re.DOTALL)
```

---

**Last Updated:** 2025-01-29T16:00:00Z  
**Success Rate:** 100% when applied correctly
