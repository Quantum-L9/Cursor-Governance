---
name: Harden and Improve Tech Debt Pipeline
overview: Implement 10 high-impact hardening and improvement measures for the Automated Tech Debt Pipeline to ensure long-term utility and systematic tech debt elimination.
todos:
  - id: circuit-breaker-audit-agent
    content: Implement Circuit Breaker in perplexity_audit_agent.py
    status: completed
  - id: audit-to-spec-bridge
    content: Develop AuditToSpecBridge for CGA integration
    status: completed
  - id: noqa-debt-eliminator
    content: Implement NoqaDebtEliminator pipeline
    status: completed
  - id: tech-debt-metrics
    content: Add tech debt metrics to Prometheus exporter
    status: completed
  - id: fix-learning-loop
    content: Integrate learning loop with Memory Substrate for fixes
    status: completed
isProject: false
---

1. **Resilience & Error Handling**:
  - Implement Circuit Breaker and Exponential Backoff in `[scripts/perplexity_audit_agent.py](scripts/perplexity_audit_agent.py)`.
  - Add failure packet emission to `MemorySubstrateService` for audit failures.
2. **Integration & Automation**:
  - Develop `AuditToSpecBridge` to convert Perplexity findings into `CodeGenAgent` (CGA) YAML specs.
  - Integrate `CGA` as a programmatic service within the pipeline.
3. **Self-Correction & Validation**:
  - Implement `ValidationSelfCorrector` in `[core/codegen/gatekeeper/codegen_gatekeeper.py](core/codegen/gatekeeper/codegen_gatekeeper.py)` to auto-fix minor validation errors (syntax, imports).
  - Add retry logic for validation failures with learning from previous attempts.
4. **Systematic Debt Elimination**:
  - Create `NoqaDebtEliminator` to track and systematically remove `# noqa` comments.
  - Implement `SQLInjectionFixer` to auto-parameterize vulnerable queries detected by audits.
  - Automate ADR-0019 (logging) and ADR-0087 (SQL) violation fixes.
5. **Observability & Metrics**:
  - Add tech debt specific metrics to `[core/observability/prometheus_exporter.py](core/observability/prometheus_exporter.py)`.
  - Implement E2E pipeline tracing using OpenTelemetry spans.
6. **Compliance & Learning**:
  - Enforce DORA block completeness in `[core/codegen/dora/dora_generator.py](core/codegen/dora/dora_generator.py)` during generation.
  - Integrate `MemorySubstrate` learning loop to store and retrieve successful fix patterns.

