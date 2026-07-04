---
# === SUITE 6 CANONICAL HEADER ===
suite: "L9 Governance"
version: "6.0.0"
component_id: "FND-AG-001"
component_name: "Constellation Linter Agent"
layer: "foundation"
domain: "agent_validation"
type: "linter_agent"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-10-28T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["FND-LG-002"]
integrates_with: ["EXE-VAL-001", "OPS-OPS-001"]
api_endpoints: ["/api/v1/lint/agents", "/api/v1/lint/compliance-check"]
data_sources: ["foundation/logic/rule-registry.json", "intelligence/reasoning/"]
outputs: ["telemetry/logs/linting-results.log", "foundation/agents/compliance-reports/"]

# === OPERATIONAL METADATA ===
execution_mode: "automatic"
monitoring_required: true
logging_level: "info"
performance_tier: "batch"

# === BUSINESS METADATA ===
purpose: "Scan agents for governance compliance using formal logic validation"
summary: "CI/CD integrated linter that validates agent configurations against governance rules"
business_value: "Ensures all agents comply with governance standards before deployment"
success_metrics: ["scan_accuracy >= 99%", "false_positive_rate < 5%", "scan_time < 30s"]

# === INTEGRATION METADATA ===
suite_1_origin: "4_ConstellationLinter_Agent.md"
migration_notes: "Enhanced with L9 Governance integration and expanded validation capabilities"

# === TAGS & CLASSIFICATION ===
tags: ["linter", "agent_validation", "compliance_check", "ci_cd", "governance_runtime"]
keywords: ["linter", "agent", "compliance", "validation", "scan"]
related_components: ["FND-LG-002", "EXE-VAL-001", "OPS-OPS-001"]
---

# Constellation Linter Agent

## Purpose
Linter that scans agents for governance compliance using formal logic validation.

## Triggers
- PromptScan: Automated scanning of agent prompts
- ComplianceCheck: On-demand compliance validation
- DeploymentGate: Pre-deployment validation
- ContinuousMonitoring: Periodic compliance checks

## L9 Governance Enhancements
- Integration with Universal Governance Kernel for rule validation
- Real-time compliance checking via API endpoints
- Enhanced reporting with detailed violation analysis
- CI/CD pipeline integration for automated validation
- Cross-layer compliance verification

## Validation Scope
- Agent configuration compliance
- Prompt adherence to governance standards
- Integration point validation
- Security policy compliance
- Performance threshold validation

#GovernanceRuntime #Suite6
