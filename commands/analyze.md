---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "CMD-006"
component_name: "Universal Analysis Command"
layer: "intelligence"
domain: "analysis"
type: "command"
status: "active"
created: "2025-01-27T00:00:00Z"
updated: "2025-11-07T18:45:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: []
integrates_with: ["CMD-005", "INT-RSN-001", "EXE-WF-001"]
api_endpoints: []
data_sources: ["project_structure", "workflow_definitions", "n8n_workflows"]
outputs: ["comprehensive_analysis", "evaluation_reports", "improvement_recommendations"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "batch"

# === BUSINESS METADATA ===
purpose: "Execute comprehensive analysis of any target (projects, workflows, n8n automations, codebases, toolkits)"
summary: "Universal analysis command executing deep evaluation: Structure Analysis → Dependency Mapping → Performance Profiling → Security Auditing → Improvement Recommendations. Optimized for n8n workflow analysis."
business_value: "Provides comprehensive analysis capabilities for any target, with specialized n8n workflow analysis, reducing manual evaluation overhead"
success_metrics: ["analysis_completeness >= 0.95", "evaluation_accuracy >= 0.90", "recommendation_quality >= 0.88"]

# === INTEGRATION METADATA ===
suite_2_origin: "analyze-toolkit.md v1.0.0"
migration_notes: "Enhanced with Suite 6 structure, universal analysis capabilities, and specialized n8n workflow analysis"

# === TAGS & CLASSIFICATION ===
tags: ["analysis", "evaluation", "n8n", "workflow", "universal", "command"]
keywords: ["analyze", "analysis", "evaluation", "n8n", "workflow", "comprehensive"]
related_components: ["CMD-005", "INT-RSN-001", "EXE-WF-001"]
startup_required: false
mode_type: "command"
---

name: analyze-toolkit
description: Execute comprehensive analysis of any target (projects, workflows, n8n automations, codebases, toolkits)

# `/analyze-toolkit` - Universal Comprehensive Analysis

**Execute comprehensive analysis of any target: projects, n8n workflows, codebases, toolkits, or systems**

## 🎯 Analysis Targets

- **n8n Workflows** - Deep workflow analysis, node evaluation, error detection, optimization opportunities
- **Projects** - Structure, completion status, gaps, consolidation opportunities
- **Codebases** - Architecture, dependencies, patterns, technical debt
- **Toolkits** - Organization, duplicates, standardization, consolidation
- **Systems** - Performance, security, reliability, scalability

## 📊 Analysis Framework

### Step 1: Target Identification & Context Loading
**For n8n Workflows:**
- Load `.n8n.json` workflow definitions
- Identify workflow triggers, nodes, connections
- Map data flow and transformation points
- Extract error handling and retry logic

**For Projects/Codebases:**
- Analyze directory structure and organization
- Identify key components and modules
- Map dependencies and relationships
- Assess naming conventions and standards

### Step 2: Structure Analysis (7-Block Reasoning)
**Source:** `@.cursor-commands/profiles/reasoning_n8n.md` (for n8n) or general reasoning

- **Abductive Analysis** - Pattern discovery, identify most likely issues/opportunities
- **Deductive Analysis** - Logical validation against best practices and standards
- **Inductive Analysis** - Generalize patterns and predict outcomes

**For n8n Workflows:**
- Detect inefficient node chains
- Identify missing error handling
- Find optimization opportunities
- Validate workflow governance compliance

**For Projects:**
- Detect duplicates and near-duplicates
- Identify organizational issues
- Validate naming conventions
- Assess structure consistency

### Step 3: Dependency & Flow Mapping
**For n8n Workflows:**
- Map node dependencies and execution order
- Identify data transformation points
- Trace error propagation paths
- Assess workflow complexity

**For Projects:**
- Map component dependencies
- Identify circular dependencies
- Assess coupling and cohesion
- Trace data flow

### Step 4: Performance & Quality Profiling
**For n8n Workflows:**
- Evaluate node execution efficiency
- Assess workflow execution time
- Identify bottlenecks and slow nodes
- Evaluate resource usage

**For Projects:**
- Assess code quality metrics
- Identify technical debt
- Evaluate maintainability
- Assess scalability concerns

### Step 5: Security & Reliability Auditing
**For n8n Workflows:**
- Audit authentication and authorization
- Check credential handling
- Validate input sanitization
- Assess error handling robustness

**For Projects:**
- Security vulnerability assessment
- Access control review
- Data protection evaluation
- Reliability and fault tolerance

### Step 6: Improvement Recommendations
- Prioritized action plan (High/Medium/Low)
- Specific improvement suggestions
- Impact assessment matrix
- Risk scores and dependencies
- Implementation roadmap

## 🚀 Usage

```
/analyze-toolkit [target] [options]

Targets:
  @workflow.json          - Analyze n8n workflow file
  @project/               - Analyze project directory
  @codebase/              - Analyze codebase
  @toolkit/               - Analyze toolkit structure
  [file or directory]     - Analyze any target

Options:
  --n8n                   - Force n8n workflow analysis mode
  --deep                  - Deep analysis with full dependency mapping
  --security-only         - Security-focused analysis
  --performance-only      - Performance-focused analysis
  --structure-only        - Structure and organization analysis only
  --recommendations-only   - Skip analysis, show recommendations only

Examples:
/analyze-toolkit @workflow.json
/analyze-toolkit @workflow.json --n8n --deep
/analyze-toolkit @project/ --structure-only
/analyze-toolkit @n8n-workflows/ --security-only
```

## 📋 Output Format

1. **Executive Summary** - Target overview and key findings
2. **Structure Analysis** - Organization, duplicates, gaps (7-block reasoning results)
3. **Dependency Map** - Visual representation of relationships
4. **Performance Profile** - Bottlenecks, efficiency metrics, optimization opportunities
5. **Security Audit** - Vulnerabilities, risks, compliance issues
6. **Quality Assessment** - Code quality, maintainability, technical debt
7. **Prioritized Recommendations** - High/Medium/Low priority actions with impact scores
8. **Implementation Roadmap** - Step-by-step improvement plan
9. **Your Next Prompt** - Suggested follow-up actions

## 🔧 n8n Workflow Analysis (Specialized)

When analyzing n8n workflows, the command automatically:

1. **Loads n8n Reasoning Profile** - `@.cursor-commands/profiles/reasoning_n8n.md`
2. **Workflow Structure Analysis**
   - Node count and types
   - Execution flow mapping
   - Data transformation tracking
   - Error handling coverage
3. **Node Evaluation**
   - Node selection optimality
   - Configuration best practices
   - Performance bottlenecks
   - Security considerations
4. **Workflow Governance**
   - Compliance with `@.cursor-commands/profiles/workflow-governance.md`
   - Naming conventions
   - Documentation completeness
   - Error handling standards
5. **Optimization Opportunities**
   - Node consolidation possibilities
   - Execution path optimization
   - Resource usage improvements
   - Cost reduction opportunities

## 📚 Reference

- n8n Reasoning Profile: `@.cursor-commands/profiles/reasoning_n8n.md`
- Workflow Governance: `@.cursor-commands/profiles/workflow-governance.md`
- Reasoning Framework: `@.cursor-commands/intelligence/reasoning/cursor-native-reasoning.md`
- Consolidation Command: `@.cursor-commands/commands/consolidate.md`

---

**Remember: Universal Analysis = Deep Understanding + Actionable Recommendations + Implementation Roadmap**
