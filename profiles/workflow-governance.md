---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "EXE-WF-001"
component_name: "Workflow Governance Validator"
layer: "execution"
domain: "workflow_validation"
type: "validator"
status: "active"
created: "2025-10-06T17:13:04Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["INT-ORC-001"]
integrates_with: ["EXE-OP-001", "EXE-VAL-001", "EXE-SEC-001"]
api_endpoints: []
data_sources: ["/commands/validate-workflow.md", "/security/api-key-verification.md", "/environment/env_validator.py"]
outputs: ["validation_reports", "compliance_scores", "remediation_actions"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Validate, standardize, and monitor all N8N workflows for compliance, safety, and completeness"
summary: "Workflow governance system validating schema integrity, credentials, environment alignment, and reasoning consistency"
business_value: "Ensures workflow quality and compliance with autonomous validation and remediation"
success_metrics: ["validation_accuracy >= 0.95", "compliance_rate >= 0.98", "remediation_success >= 0.90"]

# === INTEGRATION METADATA ===
suite_2_origin: "workflow-governance.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive workflow validation chain"

# === TAGS & CLASSIFICATION ===
tags: ["workflow", "governance", "validation", "n8n", "compliance"]
keywords: ["workflow", "governance", "validation", "n8n", "compliance"]
related_components: ["INT-ORC-001", "EXE-OP-001", "EXE-VAL-001", "EXE-SEC-001"]
startup_required: false
mode_type: "validation"
---

# Workflow Governance — Governance Brain

## Objective
Validate, standardize, and monitor all N8N workflows for compliance, safety, and completeness.

## Validation Chain
1. Schema integrity (via `/commands/validate-workflow.md`)
2. Credential verification (via `/security/api-key-verification.md`)
3. Environment alignment (via `/environment/env_validator.py`)
4. Reasoning and consistency check (via `/ops/reasoning-metrics.md`)

## Behavior
- Auto‑remediates failed validations
- Logs results in `/ops/logs/workflow_audit.json`
- Operates under “no pause” Option C logic
