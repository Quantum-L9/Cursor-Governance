<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-gmp-protocol
layer: reference
role: workflow_kernel
tags: [gmp, pipeline, orchestration, rollback]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-06-06
sources:
  - harvested: _framework-orchestrator (Suite-5 legacy, stripped n8n/WhatsApp notify)
  - harvested: pipelines-01, pipelines-rapid-analysis (stage failure policy, parallel groups)
--- /SKILL_META ---

Purpose:
Compose multi-step GMP or maintenance pipelines with rollback and parallel stages.
-->

# Pipeline Composition

Use when chaining validation → backup → change → verify steps (deploy, audit, maintenance).

## Stage YAML Pattern

```yaml
pipeline: {name}
risk_level: safe | moderate | high
rollback_on_error: true | false

steps:
  - id: validate
    parallel: true
    actions:
      - "static lint / wiring checks"
      - "security / secret scan"
    on_error: stop

  - id: backup
    actions:
      - "snapshot or commit checkpoint before mutate"
    on_error: stop

  - id: execute
    actions:
      - "locked GMP Phase 2 TODOs only"
    on_error: rollback

  - id: verify
    parallel: true
    actions:
      - "Phase 4 validation gates"
      - "smoke / targeted tests"
    on_error: warn | stop
```

## Rollback Triggers

1. Step exit non-zero on `on_error: stop` or `rollback`
2. Success metrics from `l9-structured-reasoning/references/success-metrics-template.md` not met
3. Phase 5 recursive verify = `DISCREPANCY_FOUND`
4. Explicit user abort

## Post-Run Report Skeleton

```markdown
# Pipeline Report: {name}
**Status:** SUCCESS | PARTIAL | FAILED
**Duration:** {min}

| Step | Action | Status | Notes |
|------|--------|--------|-------|

## Artifacts
- GMP report: reports/GMP-Report-{NNN}-{slug}.md
- Validation log: {command outputs}
```

## Stage Failure Policy

| Policy | When | Behavior |
|--------|------|----------|
| **ABORT** | Invalid structure, failed quality gate, missing backup before mutate | Stop pipeline; fix before retry |
| **WARN** | Documentation gap, non-critical advisory | Log; continue unless user opts out |
| **FLAG** | Manual review needed (e.g. deprecation) | Continue with explicit review item |

## Parallel Groups

For read-only analysis stages, batch independent work:

```yaml
parallel_group_a: [structure_scan, dependency_map]
parallel_group_b: [security_scan, performance_scan, readiness_gap]
# Synthesize after both groups complete
```

Do not parallelize mutating steps unless explicitly independent and locked in the GMP plan.

## Rules

- Pipelines MUST NOT bypass GMP modification lock — each mutate step maps to locked TODOs.
- Prefer parallel only for independent read-only checks.
- High-risk pipelines require backup stage before execute.
- Lifecycle stage definitions: `references/lifecycle-pipelines.md`.
