<!-- L9_META
l9_schema: 1
parent: l9-ci-ops
origin: migrated-from profiles/workflow-governance.md
sources: [profiles/workflow-governance.md]
tags: [workflow, validation, ci, governance]
status: active
/L9_META -->

# Workflow Governance

Validation ordering for workflow and pipeline definitions. The point is the **sequence**: each stage
makes the next one meaningful, so running them out of order produces misleading failures.

## Validation chain

1. **Schema integrity** — does the definition parse and conform to its schema? A schema error makes
   every later stage's output noise.
2. **Credential verification** — are required credentials present and of the correct scope? See
   [security/api-key-verification.md](../../../security/api-key-verification.md) and
   [credential-access-policy.md](../../l9-auditing-security/references/credential-access-policy.md).
3. **Environment alignment** — do the referenced services, paths, and variables exist in this
   environment? Most "the workflow is broken" reports are environment drift.
4. **Consistency check** — do the steps agree with each other: outputs feeding declared inputs, no
   orphaned or unreachable stages.

Diagnose in this order. A stage-4 inconsistency reported while stage 1 is failing is almost always an
artifact of the parse error.

## Failure handling

A failed validation **stops the chain**. Do not auto-remediate and continue — fix the failing stage,
re-run from that stage, and report which stage failed and why. See `45-pre-action-verification.mdc`.

## Not implemented

The original profile claimed auto-remediation of failed validations, a `workflow_audit.json` log, and
"no pause" autonomous operation. None is wired, and auto-remediation contradicts the failure-stop
rule. It also cited `commands/validate-workflow.md`, `environment/env_validator.py`, and
`ops/reasoning-metrics.md` — **none of those files exist**. Validation is performed by the repo's own
CI configuration and the checks documented in [ci-fix-workflow.md](ci-fix-workflow.md).
