<!-- L9_META
l9_schema: 1
artifact_id: canonical.template.executable_plan.v1
artifact_filename: canonical.template.executable_plan.v1.plan.md
first_class_artifact: true
schema_family: l9_execution_architecture
schema_class: canonical_document_type_template
version: 1.0.1
status: active
updated: 2026-08-21
owner: platform
layer: control_plane
role: executable_plan_template
tags: [l9, plan, template, program-execution, autonomy, first_class]
pairs_with: [canonical.schema.plan_document.v1]
/L9_META -->

# Canonical Executable Plan Template v1 — metadata

**SSOT path:** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
**GitHub:** Quantum-L9/Cursor-Governance
**Kind:** first-class operational primitive (fill-in Cursor `.plan.md`, not a plan instance)

## Purpose

Reusable executable plan template that agents copy into `.cursor/plans/<slug>_<8hex>.plan.md`.
Validated planning still emits `PLAN_DOCUMENT` JSON via `l9-plan`; this file is the default Cursor projection and the bind point for execution through `@environment/program-execution` + subordinate `@autonomy`.

## Consume

| Surface | How |
|---------|-----|
| `/l9-plan` / skill `l9-plan` | Default projection SSOT (skill path is a symlink here) |
| Cursor Build | Instance files derived from this template |
| Execution | Program Lock/Controller → autonomy packet → PE adapter |

## Projections (not SSOT)

- `skills/l9-plan/references/executable-plan.pe-autonomy.template.md` → symlink to this file
- `.cursor/plans/_TEMPLATE.plan.md` → local mirror only (`.cursor/` is gitignored)

## Not for

- Checking in repository-specific plan instances as this filename
- Free-form mutation without a Program lease
- Treating markdown completeness as executability without baseline/preflight/envelope
