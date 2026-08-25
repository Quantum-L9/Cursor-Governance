<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [plan, validation, program-execution, autonomy]
status: active
version: 4.0.0
updated: 2026-08-12
/L9_META -->

# Validation Checklist

## Skill pack

- [ ] `python3 scripts/validate_pack_structure.py .`
- [ ] `python3 scripts/validate_exemplary_skill.py .`
- [ ] `python3 scripts/route_plan.py --self-test`
- [ ] `python3 scripts/validate_plan_document.py fixtures/plan_pass.json` PASS
- [ ] `python3 scripts/validate_plan_kernel_receipt.py fixtures/plan_kernel_pass.plan.md` PASS
- [ ] fail fixtures FAIL with gate IDs
- [ ] `python3 scripts/self_test.py` PASS
- [ ] no omit-depth / rapid-skip language in doctrine
- [ ] `SKILL.md` version >= 4.0.0 and defaults to `plan-workflow-pe-autonomy.md`
- [ ] `executable-plan.pe-autonomy.template.md` is a symlink to the first-class SSOT

## Delivered plan

- [ ] PLAN_DOCUMENT emitted
- [ ] `validate_plan_document.py` PASS
- [ ] PE+autonomy Cursor `.plan.md` projected via `render_plan_pe_autonomy.py` (or hand-filled from SSOT)
- [ ] `.plan.md` retains **Execute via @environment/program-execution + autonomy**
- [ ] `validate_plan_kernel_receipt.py` PASS on the bound `.plan.md`
- [ ] Legacy `render_plan_markdown.py` output is not the sole deliverable
- [ ] GMP handoff emitted only when also chaining GMP

## Local Cursor mirror (optional but fail-closed when present)

- [ ] `python3 scripts/sync_cursor_plan_template.py` (writes `.cursor/plans/_TEMPLATE.plan.md` from SSOT)
- [ ] When `_TEMPLATE.plan.md` exists, its content matches the SSOT hash
