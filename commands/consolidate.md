---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "CMD-005"
component_name: "Consolidation Command"
layer: "intelligence"
domain: "organization"
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
integrates_with: ["CMD-001"]
api_endpoints: []
data_sources: ["file_structure", "duplicate_analysis"]
outputs: ["consolidated_structure", "cleanup_reports", "reorganization_plans"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "batch"

# === BUSINESS METADATA ===
purpose: "Execute comprehensive file consolidation and organization"
summary: "Combine Folder Analysis + Folder Reorganizer to consolidate duplicates, standardize naming, reorganize structure, and execute cleanup actions"
business_value: "Eliminates duplicate files, standardizes structure, and improves workspace organization efficiency"
success_metrics: ["duplicate_reduction >= 0.80", "structure_consistency >= 0.95", "cleanup_success >= 0.90"]

# === INTEGRATION METADATA ===
suite_2_origin: "consolidate.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure and comprehensive consolidation capabilities"

# === TAGS & CLASSIFICATION ===
tags: ["consolidation", "organization", "cleanup", "reorganization", "command"]
keywords: ["consolidate", "organization", "cleanup", "reorganize", "duplicates"]
related_components: ["CMD-001"]
startup_required: false
mode_type: "command"
---

name: consolidate
description: Execute comprehensive file consolidation, organization, and cleanup

# `/consolidate` - Comprehensive Consolidation

**Execute complete file consolidation, organization, and cleanup**

## Execution Chain

### Step 1: Analysis Phase
**Source:** `@UNIFIED_PROMPT_TOOLKIT/02_N8N_OPERATIONS/13_N8N_Reasoning/folder-analysis-prompt.md`

- Identify duplicates and near-duplicates
- Detect empty folders
- Flag naming inconsistencies
- Assess organizational structure

### Step 2: Consolidation Strategy
**Source:** `@UNIFIED_PROMPT_TOOLKIT/CLEANUP_CONSOLIDATION_ANALYSIS.md`

- Reference existing consolidation plan (Phase 1-5)
- Prioritize high-confidence moves
- Identify canonical versions
- Plan consolidation actions

### Step 3: Execution Phase
**Source:** `@UNIFIED_PROMPT_TOOLKIT/01_CORE_PROMPTS/01_High_Velocity_Prompts/folder-reorganizer.md`

- Move duplicate files to DEPRECATED with cross-references
- Consolidate navigation files into `00_QUICK_START/`
- Move scripts to `10_UTILITIES_META/`
- Rename files to kebab-case
- Standardize canonical headers

## Usage

```
/consolidate [target] [phase]

Examples:
/consolidate @UNIFIED_PROMPT_TOOLKIT/
/consolidate @UNIFIED_PROMPT_TOOLKIT/ phase1
/consolidate duplicates-only
```

## Consolidation Phases

### Phase 1: High-Confidence Moves (Immediate)
- Move cleanup scripts to utilities
- Consolidate duplicate index files
- Move duplicate style guides to DEPRECATED

### Phase 2: Consolidation (High Priority)
- Identify canonical versions
- Move duplicates to DEPRECATED with cross-references
- Consolidate meta-log-index files

### Phase 3: Renaming (Medium Priority)
- Rename Title_Case files to kebab-case
- Update all cross-references
- Verify no broken links

### Phase 4: Header Standardization (Ongoing)
- Audit files missing domain field
- Standardize domain values
- Align version numbers

### Phase 5: Structure Optimization (Lower Priority)
- Review folder structure
- Merge underutilized folders
- Create missing README files

## Output Format

- **Pre-Consolidation Report** - Current state analysis
- **Consolidation Plan** - Specific actions planned
- **Execution Log** - Files moved/renamed/updated
- **Post-Consolidation Summary** - Results and improvements
- **Verification Checklist** - Compliance validation

## Reference
- Consolidation Analysis: `@UNIFIED_PROMPT_TOOLKIT/CLEANUP_CONSOLIDATION_ANALYSIS.md`
- Folder Reorganizer: `@UNIFIED_PROMPT_TOOLKIT/01_CORE_PROMPTS/01_High_Velocity_Prompts/folder-reorganizer.md`
- Folder Analysis: `@UNIFIED_PROMPT_TOOLKIT/02_N8N_OPERATIONS/13_N8N_Reasoning/folder-analysis-prompt.md`

