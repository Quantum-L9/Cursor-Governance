---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-ORC-001"
component_name: "Governance Orchestrator"
layer: "intelligence"
domain: "orchestration"
type: "orchestrator"
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
dependencies: []
integrates_with: ["INT-RSN-001", "INT-RSN-002", "INT-RSN-003", "EXE-WF-001", "EXE-OP-001"]
api_endpoints: []
data_sources: [".cursor/rules.json", "/ops/logs/", "/environment/env_validator.py"]
outputs: ["task_delegations", "execution_orders", "reasoning_metrics"]

# === OPERATIONAL METADATA ===
execution_mode: "continuous"
monitoring_required: true
logging_level: "info"
performance_tier: "real-time"

# === BUSINESS METADATA ===
purpose: "Serve as central coordinator for all governance layers, ensuring synchronized reasoning, validation, and execution"
summary: "Central governance brain coordinating reasoning profiles, workflow governance, and operational health monitoring"
business_value: "Ensures consistent governance execution across all layers with adaptive reasoning feedback"
success_metrics: ["orchestration_accuracy >= 0.95", "layer_synchronization >= 0.98", "reasoning_quality >= 0.90"]

# === INTEGRATION METADATA ===
suite_2_origin: "orchestrator.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure, comprehensive reasoning profile integration, and adaptive telemetry monitoring"

# === TAGS & CLASSIFICATION ===
tags: ["orchestration", "governance", "coordination", "reasoning", "ynp_enabled"]
keywords: ["orchestrator", "governance", "coordination", "reasoning", "execution"]
related_components: ["INT-RSN-001", "INT-RSN-002", "INT-RSN-003", "EXE-WF-001", "EXE-OP-001"]
startup_required: true
mode_type: "orchestration"
---

# Orchestrator — Governance Brain

## Objective
Serve as the central coordinator for all governance layers, ensuring synchronized reasoning, validation, and execution under Option C (No Pause).

## Control Logic
- Loads `.cursor/rules.json`
- Enforces interlayer execution order: Environment → Security → Pipeline → Commands → OPS
- Monitors telemetry from `/ops/logs/` for adaptive reasoning feedback
- Delegates tasks to `workflow-governance.md` and `operational-health.md`

## Integration
- Reads environment via `/environment/env_validator.py`
- Calls document reasoning from `reasoning_docs.md`
- Calls technical reasoning from `reasoning_technical_operations.md`
- Calls n8n-specific reasoning from `reasoning_n8n.md` (for all n8n tasks)
- Syncs metrics to `/ops/reasoning-metrics.md`

## Reasoning Priority
- **n8n tasks**: Use `reasoning_n8n.md` (highest priority for automation work)
- **Technical decisions**: Use `reasoning_technical_operations.md`
- **Document analysis**: Use `reasoning_docs.md`

## Behavior
Autonomous • Continuous • Adaptive • YNP Enabled
