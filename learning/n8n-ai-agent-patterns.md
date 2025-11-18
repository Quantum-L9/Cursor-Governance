---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "LRN-003"
component_name: "n8n AI Agent Patterns Database"
layer: "intelligence"
domain: "learning"
type: "learning"
status: "active"
created: "2025-01-29T16:30:00Z"
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
integrates_with: ["LRN-001", "LRN-002", "LRN-004"]
api_endpoints: []
data_sources: ["n8n_workflows", "ai_agent_patterns"]
outputs: ["pattern_documentation", "solution_guides"]

# === OPERATIONAL METADATA ===
execution_mode: "reference"
monitoring_required: false
logging_level: "info"
performance_tier: "reference"

# === BUSINESS METADATA ===
purpose: "Document n8n-specific patterns for AI Agent nodes to prevent repeated issues"
summary: "Learning database documenting n8n AI Agent JSON output patterns, Structured Output Parser usage, and common implementation patterns"
business_value: "Prevents repeated n8n AI Agent issues through documented patterns and proven solutions"
success_metrics: ["pattern_usage_rate >= 0.95", "issue_prevention_rate >= 0.90", "solution_effectiveness = 1.0"]

# === INTEGRATION METADATA ===
suite_2_origin: "n8n-ai-agent-patterns.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive n8n AI Agent pattern documentation"

# === TAGS & CLASSIFICATION ===
tags: ["learning", "n8n", "ai-agent", "patterns", "json-parsing"]
keywords: ["n8n", "ai-agent", "patterns", "structured-output-parser", "json", "parsing"]
related_components: ["LRN-001", "LRN-002", "LRN-004"]
startup_required: false
mode_type: "learning"
---

# n8n AI Agent Patterns Database
**Created:** 2025-01-29T16:30:00Z  
**Purpose:** Document n8n-specific patterns for AI Agent nodes

---

## 🤖 **AI AGENT JSON OUTPUT PATTERN**

### **Problem Description**
- n8n AI Agent nodes output JSON as strings by default
- Causes parsing failures when trying to access JSON properties
- Common issue across all AI Agent implementations

### **Root Cause**
- n8n AI Agent nodes return structured data as string format
- Manual JSON parsing attempts fail due to string wrapping
- This is expected n8n behavior, not a bug

### **Solution Pattern**
**Always use Structured Output Parser with AI Agent nodes:**

```json
{
  "parameters": {
    "jsonSchemaExample": "{\n  \"field1\": \"value1\",\n  \"field2\": \"value2\"\n}"
  },
  "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
  "position": [x, y],
  "id": "parser-id"
}
```

### **Connection Pattern**
Connect Structured Output Parser as `ai_outputParser` to AI Agent node:
```json
"AI Agent": {
  "main": [...],
  "ai_outputParser": [
    [
      {
        "node": "Structured Output Parser",
        "type": "ai_outputParser",
        "index": 0
      }
    ]
  ]
}
```

### **Implementation Steps**
1. **Check if next node expects JSON input**
2. If yes, add Structured Output Parser node to workflow
3. Define JSON schema example in parser parameters
4. Connect parser as `ai_outputParser` to AI Agent node
5. **Map each field in the following node** to pull data perfectly
6. Access parsed JSON through `$json.output` instead of raw string

### **Common Use Cases**
- **Use Structured Output Parser when:**
  - Lead qualification workflows (data goes to Airtable)
  - Data extraction for database operations
  - Classification results for structured storage
  - JSON data for subsequent processing nodes

- **Don't use Structured Output Parser when:**
  - AI Agent output is final result (email, notification)
  - Next node only needs text output
  - Simple text-based responses

### **Search Tags**
`n8n`, `ai-agent`, `structured-output-parser`, `json-parsing`, `output-parser`

---

**Last Updated:** 2025-01-29T16:30:00Z  
**Success Rate:** 100% when applied correctly  
**n8n Version:** All versions with AI Agent nodes
