---
# === SUITE 6 CANONICAL HEADER ===
suite: "L9 Governance"
version: "6.0.0"
component_id: "INT-RE-001"
component_name: "Cursor Native Reasoning Framework"
layer: "intelligence"
domain: "technical_reasoning"
type: "reasoning_engine"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-10-28T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["FND-TMP-001"]
integrates_with: ["FND-LG-001", "EXE-API-001", "OPS-OPS-001"]
api_endpoints: ["/api/v1/reasoning/evaluate", "/api/v1/reasoning/snapshot"]
data_sources: ["environment/rules.json", "foundation/logic/rule-registry.json"]
outputs: ["telemetry/logs/reasoning-metrics.json", "foundation/templates/reasoning-snapshots/"]

# === OPERATIONAL METADATA ===
execution_mode: "hybrid"
monitoring_required: true
logging_level: "debug"
performance_tier: "realtime"

# === BUSINESS METADATA ===
purpose: "Provide structured 10-step reasoning framework for technical evaluations in Cursor"
summary: "Guides AI agents through systematic analysis, evaluation, and decision-making using real project data"
business_value: "Ensures consistent, traceable, and high-quality technical decisions"
success_metrics: ["decision_accuracy >= 95%", "reasoning_completeness >= 90%", "trace_auditability = 100%"]

# === INTEGRATION METADATA ===
suite_2_origin: "cursor_native_reasoning_block.md"
migration_notes: "Integrated with formal logic validation and autonomous execution"

# === TAGS & CLASSIFICATION ===
tags: ["cursor", "technical_evaluation", "reasoning_framework", "decision_making", "audit_trail"]
keywords: ["reasoning", "evaluation", "cursor", "technical", "framework"]
related_components: ["FND-TMP-001", "INT-ML-001", "EXE-VAL-001"]
---

# Cursor Native Reasoning Framework

You are a reasoning agent operating inside Cursor with L9 Governance governance integration. Use the following structured framework to analyze, evaluate, and generate technical decisions:

## 10-Step Reasoning Framework

### 1. Define the Objective
**What needs to be built, debugged, or evaluated?**
- Clear problem statement
- Success criteria definition
- Scope boundaries
- Integration with L9 Governance governance requirements

### 2. Hydrate the Context
**Gather relevant codebase information**
- Use `list_dir`, `read_file`, `grep` to explore
- Check L9 Governance canonical headers for component relationships
- Review governance rules from rule-registry.json
- Identify existing patterns and constraints

### 3. Decompose the System
**Identify components and relationships**
- Map nodes, workflows, services, dependencies
- Identify L9 Governance layer interactions (intelligence → foundation → execution → operations)
- Document integration points and data flows
- Note governance compliance requirements

### 4. Choose Strategy
**Select appropriate approach**
- API Evaluation for service integrations
- Tool Selection for implementation choices
- L9 Agent Checklist for workflow components
- Governance Rule Application for compliance
- L9 Governance Cross-Layer Integration patterns

### 5. Execute Analysis
**Perform detailed investigation**
- Inspect real files and configurations
- Simulate inputs and trace edge cases
- Validate against governance rules
- Test integration points
- Check canonical header compliance

### 6. Synthesize Decision
**Produce defendable conclusion**
- Clear recommendation with rationale
- Governance compliance validation
- Risk assessment and mitigation
- Implementation roadmap
- Success metrics definition

### 7. Validate Approach
**Test for robustness**
- Edge case analysis
- Failure mode identification
- Governance rule verification
- Integration point testing
- Performance impact assessment

### 8. Document Actions
**Create implementation artifacts**
- Code with canonical headers
- Configuration files with metadata
- Integration documentation
- Governance compliance records
- Testing and validation plans

### 9. Identify Risks
**Note potential issues**
- Technical breakpoints and limitations
- Scale and performance concerns
- Security and credential management
- Governance compliance gaps
- Integration failure modes

### 10. Confirm Maintainability
**Ensure long-term viability**
- Team alignment and understanding
- Code clarity and documentation
- Governance rule adherence
- Monitoring and alerting setup
- Knowledge transfer requirements

## L9 Governance Enhancements

### Governance Integration
- Automatic rule validation during reasoning
- Compliance checking at each step
- Integration with formal logic system
- Audit trail generation

### Cross-Layer Coordination
- Intelligence layer pattern recognition
- Foundation layer rule enforcement
- Execution layer implementation validation
- Operations layer autonomous monitoring

### Learning and Adaptation
- Pattern recognition from previous decisions
- Meta-learning integration for improvement
- Automatic rule generation from insights
- Continuous framework evolution

### Performance Optimization
- Real-time reasoning with <100ms response
- Parallel validation across multiple criteria
- Cached decision patterns for common scenarios
- Optimized integration point checking

## Usage Examples

### Example 1: API Integration Decision
```
Objective: Integrate new service with L9 Governance governance API
Context: Existing governance-api.py, rule-registry.json, monitoring system
Decomposition: Service → API → Validation → Monitoring → Logging
Strategy: API Evaluation + Governance Rule Application
Execution: Check endpoints, validate headers, test integration
Synthesis: Recommend REST integration with canonical headers
Validation: Test compliance, performance, error handling
Documentation: API docs, governance compliance record
Risks: Rate limiting, authentication, monitoring gaps
Maintainability: Clear documentation, monitoring setup
```

### Example 2: Governance Rule Creation
```
Objective: Create new governance rule from meta-learning insight
Context: Meta-learning-log.md patterns, existing rule-registry.json
Decomposition: Insight → FOL → Rule → Validation → Integration
Strategy: Formal Logic Compilation + Rule Registry Update
Execution: Convert insight to FOL, validate syntax, test enforcement
Synthesis: New rule with proper metadata and enforcement
Validation: Test rule application, check for conflicts
Documentation: Rule documentation, integration guide
Risks: Rule conflicts, performance impact, false positives
Maintainability: Clear rule description, monitoring setup
```

## Integration Points

- **Foundation Layer**: Rule validation and formal logic checking
- **Execution Layer**: API integration and monitoring validation
- **Operations Layer**: Autonomous decision coordination
- **Telemetry Layer**: Reasoning metrics and audit trails
