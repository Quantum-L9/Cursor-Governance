---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "CMD-007"
component_name: "Comprehensive Project Evaluation Command"
layer: "intelligence"
domain: "evaluation"
type: "command"
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
integrates_with: ["CMD-001", "CMD-002"]
api_endpoints: []
data_sources: ["project_structure", "completion_status"]
outputs: ["evaluation_reports", "gap_analyses", "refinement_plans"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "batch"

# === BUSINESS METADATA ===
purpose: "Execute comprehensive project evaluation and refinement"
summary: "Chain command combining Project Completion Agent + Folder Analysis + Ultimate Master Guide for complete project evaluation, gap identification, and refinement opportunities"
business_value: "Provides comprehensive project evaluation in single command, identifying gaps and refinement opportunities efficiently"
success_metrics: ["evaluation_completeness >= 0.95", "gap_detection_rate >= 0.90", "refinement_quality >= 0.88"]

# === INTEGRATION METADATA ===
suite_2_origin: "evaluate- Comprehensive Project Evaluation.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive evaluation capabilities"

# === TAGS & CLASSIFICATION ===
tags: ["evaluation", "analysis", "project-completion", "refinement", "command"]
keywords: ["evaluate", "evaluation", "project", "analysis", "refinement", "gaps"]
related_components: ["CMD-001", "CMD-002"]
startup_required: false
mode_type: "command"
---

name: evaluate
description: Execute comprehensive project evaluation, refinement, and gap analysis

# `/evaluate` - Comprehensive Project Evaluation

**Execute complete project evaluation, refinement, and gap analysis**

## Execution Chain

### Step 1: Project Status Analysis
**Source:** `@UNIFIED_PROMPT_TOOLKIT/01_CORE_PROMPTS/01_High_Velocity_Prompts/project_completion_agent.prompt.md`

- Determine current project status (% complete per phase)
- Identify gaps between current state and launch-ready state
- Flag consolidation opportunities, duplicates, organizational issues
- Generate prioritized action plan with specific deliverables

### Step 2: Folder Structure Analysis
**Source:** `@UNIFIED_PROMPT_TOOLKIT/02_N8N_OPERATIONS/13_N8N_Reasoning/folder-analysis-prompt.md`

- Execute 7-block reasoning analysis (Abductive + Deductive + Inductive)
- Detect duplicates, near-duplicates, empty folders
- Validate naming conventions, header compliance, structure
- Generate consolidation recommendations with impact scores

### Step 3: Comprehensive System Assessment
**Source:** `@UNIFIED_PROMPT_TOOLKIT/02_N8N_OPERATIONS/09_N8N_Power_Commands/ultimate-master-guide.md`

- Deep system analysis
- Dependency mapping
- Performance profiling
- Security auditing

## Usage

```
/evaluate [target]

Examples:
/evaluate @UNIFIED_PROMPT_TOOLKIT/
/evaluate current-project
/evaluate workspace-structure
```

## Output Format

- **Executive Summary** - Project status overview
- **Detailed Findings** - Duplicates, gaps, opportunities
- **Prioritized Action Plan** - High/Medium/Low priority actions
- **Execution Checklist** - Specific file moves/renames
- **Impact Assessment** - Risk scores and dependencies
- **Your Next Prompt** - Suggested follow-up actions

## Reference
- Project Completion Agent: `@UNIFIED_PROMPT_TOOLKIT/01_CORE_PROMPTS/01_High_Velocity_Prompts/project_completion_agent.prompt.md`
- Folder Analysis: `@UNIFIED_PROMPT_TOOLKIT/02_N8N_OPERATIONS/13_N8N_Reasoning/folder-analysis-prompt.md`
- Ultimate Master Guide: `@UNIFIED_PROMPT_TOOLKIT/02_N8N_OPERATIONS/09_N8N_Power_Commands/ultimate-master-guide.md`

