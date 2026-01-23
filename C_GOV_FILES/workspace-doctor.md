---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "PIP-005"
component_name: "Workspace Doctor Governance Layer"
layer: "execution"
domain: "pipeline"
type: "pipeline"
status: "active"
created: "2025-01-27T00:00:00Z"
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
integrates_with: ["PIP-001", "EXE-OP-001", "EXE-SEC-001"]
api_endpoints: []
data_sources: ["workspace_state", "environment_configs", "workflow_integrity"]
outputs: ["health_reports", "remediation_actions"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "batch"

# === BUSINESS METADATA ===
purpose: "Perform full workspace health checks to confirm readiness for deployment, completeness, and compliance with governance standards"
summary: "10X Governance Layer providing comprehensive workspace health checks with automatic remediation and compliance verification"
business_value: "Ensures workspace readiness and compliance through comprehensive health checks and automatic remediation"
success_metrics: ["health_score >= 0.90", "remediation_success_rate >= 0.95", "compliance_rate >= 1.0"]

# === INTEGRATION METADATA ===
suite_2_origin: "workspace-doctor.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive workspace health check capabilities"

# === TAGS & CLASSIFICATION ===
tags: ["pipeline", "workspace", "health", "doctor", "governance"]
keywords: ["workspace", "doctor", "health", "check", "compliance", "remediation"]
related_components: ["PIP-001", "EXE-OP-001", "EXE-SEC-001"]
startup_required: false
mode_type: "pipeline"
---

# Workspace Doctor — 10X Governance Layer

## Objective
Perform full workspace health checks to confirm readiness for deployment, completeness, and compliance with governance standards.

## Evaluation Metrics
- Environment Sync Status
- Version Consistency
- Workflow Integrity
- Security Posture
- Operational Health Score

## Scoring
Each metric returns a numeric value (0–100). A final report is written to `/logs/workspace_health_report.json`.

## Auto-Fix
- Missing `.env` triggers environment loader.
- Missing dependencies trigger `preflight-check.md`.
- Deviations auto-remediated based on governance profiles.

## Behavior
Autonomous, continuous, and non-blocking.
