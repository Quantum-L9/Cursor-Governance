---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "OPS-002"
component_name: "Memory Aggregator Operations Layer"
layer: "operations"
domain: "memory"
type: "operations"
status: "active"
created: "2025-10-06T17:10:32Z"
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
integrates_with: ["INT-IMP-001", "INT-REF-001"]
api_endpoints: []
data_sources: ["chat_exports", "system_logs"]
outputs: ["memory_index", "learning_summaries"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "batch"

# === BUSINESS METADATA ===
purpose: "Aggregate chat exports and system logs into a structured Governance Memory Ledger"
summary: "OPS Canonical layer aggregating chat exports and system logs into structured memory ledger with success scoring and learning extraction"
business_value: "Enables learning from historical interactions through structured memory aggregation"
success_metrics: ["aggregation_completeness >= 0.95", "learning_extraction_rate >= 0.90", "memory_quality >= 0.88"]

# === INTEGRATION METADATA ===
suite_2_origin: "memory-aggregator.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive memory aggregation capabilities"

# === TAGS & CLASSIFICATION ===
tags: ["operations", "memory", "aggregator", "learning", "governance"]
keywords: ["memory", "aggregator", "learning", "ledger", "governance", "scoring"]
related_components: ["INT-IMP-001", "INT-REF-001"]
startup_required: false
mode_type: "operations"
---

Version: 1.0.0
Canonical-Source: 10X Governance Suite
Generated: 2025-10-06T17:10:32Z

# Memory Aggregator — OPS Canonical

## Objective
Aggregate chat exports and system logs into a structured Governance Memory Ledger.

## Function
- Ingests `/ops/logs/chat_exports/*`.
- Extracts methodologies, outcomes, and reasoning patterns.
- Updates `/ops/logs/memory_index.json`.

## Scoring Rubric
- Success = +1.0 weight
- Partial = +0.5 weight
- Failure = -1.0 weight

## Policy
`.cursor/rules.json` → `apply_best_known_method`

## Output
Summarized learnings appended to `/ops/logs/memory_index.json` with timestamps.
