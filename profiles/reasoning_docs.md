---
# === SUITE 6 CANONICAL HEADER ===
suite: "L9 Governance"
version: "6.0.0"
component_id: "INT-RSN-002"
component_name: "Strategic Document Reasoning Profile"
layer: "intelligence"
domain: "reasoning"
type: "reasoning_profile"
status: "active"
created: "2025-10-10T00:00:00Z"
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
integrates_with: ["INT-RSN-001", "INT-RSN-003"]
api_endpoints: []
data_sources: ["workspace_documents", "strategic_intelligence"]
outputs: ["dependency_maps", "gap_analyses", "coherence_reports", "strategic_insights"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Enable advanced multi-layered analysis for documentation-heavy workspaces with strategic intelligence"
summary: "Strategic reasoning profile providing chain-of-thought analysis, pattern recognition, analogical reasoning, and reflective logic for complex document structures"
business_value: "Transforms document-heavy projects into actionable strategic insights with enterprise-grade analytical capabilities"
success_metrics: ["insight_accuracy >= 0.85", "gap_detection_rate >= 0.90", "coherence_improvement >= 0.15"]

# === INTEGRATION METADATA ===
suite_2_origin: "reasoning_docs.md v2.0.0"
migration_notes: "Enhanced with L9 Governance structure, comprehensive reasoning modes, and strategic intelligence integration"

# === TAGS & CLASSIFICATION ===
tags: ["reasoning", "strategic", "document_analysis", "intelligence", "pattern_recognition"]
keywords: ["reasoning", "strategic", "documents", "analysis", "pattern", "coherence", "gaps"]
related_components: ["INT-RSN-001", "INT-RSN-003", "INT-ORC-001"]
startup_required: true
mode_type: "reasoning"
---

# Reasoning Profile — Strategic Intelligence Layer

---

## 🎯 Purpose

The Reasoning Profile enables advanced multi-layered analysis for documentation-heavy workspaces. It provides chain-of-thought analysis, pattern recognition, analogical reasoning, and reflective logic to extract strategic insights from complex document structures.

---

## 🧠 Reasoning Modes

### 1. Chain-of-Thought Analysis
**Use Case**: Understanding complex relationships across documents

**Process**:
1. **Identify starting point** (document, concept, or requirement)
2. **Trace dependencies** through document references
3. **Map logical flow** of information and decisions
4. **Document reasoning chain** for transparency
5. **Identify gaps or breaks** in logical flow

**Example**:
```
Starting Point: "Waste Management Policy Framework"
→ References: "Regulatory Requirements" 
→ Depends on: "LCDS Chapter 3"
→ Implements: "Georgetown Modernization Plan"
→ Supports: "Stakeholder Communications"
→ Gap Found: Missing implementation timeline
```

**Output**: Dependency chain with gap analysis

---

### 2. Pattern Recognition
**Use Case**: Identifying recurring themes, structures, or issues

**Process**:
1. **Scan document corpus** for repeated patterns
2. **Classify patterns** by type (structural, conceptual, procedural)
3. **Measure pattern frequency** and significance
4. **Identify anomalies** or deviations from patterns
5. **Generate pattern report** with recommendations

**Pattern Types**:
- **Structural**: Document organization, section formats
- **Conceptual**: Recurring themes, key concepts
- **Procedural**: Repeated processes, workflows
- **Relational**: Common document relationships
- **Temporal**: Timeline patterns, milestones

**Example Output**:
```
Pattern: "Stakeholder Engagement" appears in 15 documents
Pattern: Implementation timelines consistently 18-24 months
Anomaly: "Tire Recycling" lacks financial model (others have)
Recommendation: Standardize financial model across all waste types
```

---

### 3. Analogical Reasoning
**Use Case**: Applying solutions from one domain to another

**Process**:
1. **Identify problem domain** (e.g., hazardous waste management)
2. **Find analogous solved problems** (e.g., e-waste management)
3. **Map structural similarities** between domains
4. **Adapt solution approach** to new domain
5. **Validate applicability** and identify limitations

**Example**:
```
Problem: No hazardous waste pricing model
Analogous Case: E-waste pricing model exists
Similarities: Both need specialized handling, certification, tracking
Adaptation: Apply tiered pricing based on hazard classification
Validation: Requires regulatory approval (different from e-waste)
```

**Output**: Adapted solution with validation notes

---

### 4. Reflective Logic
**Use Case**: Self-assessment and improvement opportunities

**Process**:
1. **Review completed analysis** or recommendations
2. **Question assumptions** made during analysis
3. **Identify potential biases** or blind spots
4. **Consider alternative interpretations**
5. **Refine conclusions** based on reflection

**Reflection Questions**:
- What assumptions did we make?
- What evidence contradicts our conclusion?
- What perspectives are we missing?
- How confident are we in this analysis?
- What could we do better next time?

**Example**:
```
Initial Conclusion: "All stakeholders aligned on timeline"
Reflection: Based only on written documents, no interview data
Alternative View: Written alignment ≠ true commitment
Refined Conclusion: "Documented alignment exists; validation needed"
Confidence: Medium (60%) - requires stakeholder interviews
```

---

### 5. Meta-Analysis
**Use Case**: Analysis of analyses, system-level insights

**Process**:
1. **Aggregate insights** from multiple analyses
2. **Identify meta-patterns** across analysis types
3. **Assess overall system health** and coherence
4. **Generate strategic recommendations**
5. **Prioritize actions** based on impact and feasibility

**Meta-Metrics**:
- **Coherence Score**: How well documents align (0-100)
- **Completeness Score**: Coverage of required topics (0-100)
- **Redundancy Index**: Duplicate content percentage
- **Gap Severity**: Critical vs. minor gaps
- **Strategic Readiness**: Ready for next phase? (Yes/No/Partial)

**Example Output**:
```
Coherence: 85/100 (Strong alignment across strategic docs)
Completeness: 72/100 (Missing: vendor contracts, insurance specs)
Redundancy: 15% (Multiple versions of implementation plan)
Critical Gaps: 3 (Financing terms, regulatory approvals, insurance)
Strategic Readiness: PARTIAL (Address 3 critical gaps first)
```

---

## 🔧 Reasoning Operations

### Operation 1: Document Dependency Mapping
**Command**: `@reasoning.md map-dependencies [start-document]`

**Process**:
1. Parse document for references (links, citations, mentions)
2. Build directed graph of dependencies
3. Identify critical path documents
4. Detect circular dependencies
5. Generate visual map (text-based tree)

**Output Format**:
```
Document Dependency Map: "Georgetown Waste Modernization Plan"

Level 1 (Foundation):
  └─ Guyana Green State Development Strategy
  └─ LCDS Chapter 3 & 4
  └─ PPP Manifesto Summary

Level 2 (Requirements):
  └─ Regulatory Framework Overview
  └─ Waste Policy Framework
  └─ Market Opportunity Assessment

Level 3 (Implementation):
  └─ Detailed Implementation Plan [CRITICAL PATH]
  └─ Technology Platform Integration
  └─ Financial Model

Circular Dependency: None
Missing Dependencies: Insurance specifications (referenced but not found)
```

---

### Operation 2: Knowledge Gap Analysis
**Command**: `@reasoning.md analyze-gaps [scope]`

**Process**:
1. Identify all referenced topics/documents
2. Verify existence and completeness
3. Classify gaps by severity (Critical, Major, Minor)
4. Assess impact on project readiness
5. Generate prioritized gap-filling plan

**Gap Classification**:
- **Critical**: Blocks progress, immediate action needed
- **Major**: Significant impact, address soon
- **Minor**: Nice-to-have, can be deferred
- **Informational**: No action needed, just awareness

**Example Output**:
```
Knowledge Gap Analysis: "Guyana Waste Management Project"

CRITICAL GAPS (3):
1. Vendor financing terms not documented
   Impact: Cannot proceed with equipment procurement
   Action: Create vendor financing term sheet
   
2. Insurance program specifications missing
   Impact: Risk exposure undefined, liability unclear
   Action: Develop comprehensive insurance spec
   
3. Regulatory approval timeline undefined
   Impact: Project timeline at risk
   Action: Map regulatory approval process with dates

MAJOR GAPS (5):
[detailed list...]

MINOR GAPS (12):
[detailed list...]

Priority Action Plan:
Week 1: Address Critical Gap #1 (vendor financing)
Week 2: Address Critical Gap #2 (insurance)
Week 3: Address Critical Gap #3 (regulatory timeline)
```

---

### Operation 3: Strategic Coherence Check
**Command**: `@reasoning.md check-coherence [document-set]`

**Process**:
1. Extract key claims/statements from each document
2. Check for contradictions across documents
3. Verify consistency of data (dates, numbers, names)
4. Identify conflicting recommendations
5. Generate coherence report with conflicts highlighted

**Example Output**:
```
Strategic Coherence Check: "All Waste Management Documents"

CONTRADICTIONS FOUND (2):
1. Timeline Conflict:
   - "Implementation Plan" states: 18-month timeline
   - "Minister Presentation" states: 24-month timeline
   Resolution: Clarify official timeline in Master Plan

2. Financial Model Conflict:
   - "Financial Model" shows: $4.2M CAPEX
   - "Budget Annex" shows: $3.8M CAPEX
   Resolution: Reconcile numbers, identify source of $400K difference

DATA INCONSISTENCIES (4):
[detailed list...]

OVERALL COHERENCE: 85/100 (GOOD)
Recommendation: Resolve 2 contradictions before stakeholder meetings
```

---

### Operation 4: Strategic Insight Generation
**Command**: `@reasoning.md generate-insights [focus-area]`

**Process**:
1. Apply all reasoning modes to focus area
2. Synthesize findings into actionable insights
3. Prioritize by strategic value
4. Generate executive summary
5. Create action recommendations

**Insight Types**:
- **Opportunities**: Unidentified value creation paths
- **Risks**: Potential failure points or vulnerabilities
- **Efficiencies**: Ways to do more with less
- **Innovations**: Novel approaches or combinations
- **Quick Wins**: High-value, low-effort actions

**Example Output**:
```
Strategic Insights: "Carbon Credits Revenue Stream"

OPPORTUNITY INSIGHT:
Ocean-bound plastic collection could generate additional carbon credits
beyond landfill diversion. Research shows 2.1x multiplier effect.
Potential Value: +$3.2M annually
Action: Add ocean-bound plastic program to Georgetown coastal areas

RISK INSIGHT:
Carbon credit verification process takes 9-12 months. Revenue model
assumes immediate cash flow. Creates $1.8M funding gap in Year 1.
Mitigation: Secure bridge financing or adjust revenue projections

EFFICIENCY INSIGHT:
Three separate waste collection routes overlap 40% in Georgetown.
Route optimization could reduce fuel costs by $180K annually.
Action: Implement AMCS routing optimization in Phase 1

INNOVATION INSIGHT:
Combining tire recycling with asphalt production creates closed-loop
system. Guyana imports 100% of asphalt. Potential import substitution.
Strategic Value: Energy independence narrative + cost savings

QUICK WIN:
School education program documents exist but not deployed. Deploy
immediately to build community support before major operations begin.
Timeline: 2 weeks | Cost: $5K | Value: High public support
```

---

## 🎯 Reasoning Triggers

### Automatic Triggers
These reasoning operations run automatically:

1. **On workspace analysis**: Run coherence check
2. **On document save**: Update dependency map
3. **Before strategic backup**: Run gap analysis
4. **On monthly schedule**: Generate strategic insights
5. **On request**: Any manual reasoning operation

### Manual Triggers
User can invoke any reasoning operation:

```bash
@reasoning.md map-dependencies "Georgetown Modernization Plan"
@reasoning.md analyze-gaps --critical-only
@reasoning.md check-coherence --all-documents
@reasoning.md generate-insights "Hazardous Waste Services"
```

---

## 📊 Integration with Strategic Intelligence

The Reasoning Profile integrates with the Strategic Intelligence Command to provide:

1. **Document Intelligence**: Powered by chain-of-thought analysis
2. **Workspace Integrity**: Powered by coherence checking
3. **Strategic Analysis**: Powered by insight generation
4. **Gap Detection**: Powered by gap analysis
5. **Knowledge Mapping**: Powered by dependency mapping

---

## 🔄 Continuous Learning

The Reasoning Profile learns and improves over time:

1. **Pattern Library**: Builds repository of common patterns
2. **Solution Database**: Stores successful analogical solutions
3. **Gap History**: Tracks recurring gap types
4. **Insight Effectiveness**: Measures which insights led to action
5. **Refinement Loop**: Improves reasoning based on outcomes

---

## 📈 Success Metrics

### Quality Metrics
- **Insight Accuracy**: % of insights that prove valuable
- **Gap Detection Rate**: % of gaps found vs. missed
- **Coherence Improvement**: Change in coherence score over time
- **Pattern Recognition**: % of patterns successfully identified

### Impact Metrics
- **Time Saved**: Hours saved through automated analysis
- **Risk Mitigation**: Issues identified before they become problems
- **Strategic Value**: Estimated $ value of insights generated
- **Decision Quality**: Better decisions from better analysis

---

## 🚀 Usage Examples

### Example 1: Pre-Meeting Preparation
```bash
@reasoning.md generate-insights "Minister Presentation Materials"
@reasoning.md check-coherence "Stakeholder Communications"
@reasoning.md analyze-gaps --blocking-issues-only
```

**Output**: Executive briefing with key insights, any contradictions to resolve, and blocking issues to address before meeting

---

### Example 2: Project Health Check
```bash
@reasoning.md map-dependencies --all
@reasoning.md check-coherence --comprehensive
@reasoning.md generate-insights --opportunities-and-risks
```

**Output**: Complete project health assessment with dependency map, coherence report, and strategic insights

---

### Example 3: Gap Closure Sprint
```bash
@reasoning.md analyze-gaps --critical
@reasoning.md map-dependencies --reverse-lookup [missing-document]
@reasoning.md generate-insights --efficiency
```

**Output**: Prioritized gap list, impact analysis, and efficient approaches to close gaps

---

## 🔐 Quality Standards

### Analysis Quality
- **Evidence-Based**: All insights tied to specific documents
- **Traceable**: Clear reasoning chain from evidence to conclusion
- **Validated**: Cross-checked against multiple sources
- **Transparent**: Confidence levels and assumptions stated
- **Actionable**: Insights lead to specific actions

### Output Quality
- **Clear**: Understandable by executives and practitioners
- **Concise**: Focus on high-value insights, not data dumps
- **Structured**: Consistent format for easy consumption
- **Prioritized**: Most important items highlighted
- **Complete**: All relevant context included

---

**This Reasoning Profile powers the Strategic Intelligence Command with enterprise-grade analytical capabilities for documentation-intensive strategic projects.**
