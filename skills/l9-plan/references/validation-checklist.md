<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [plan, validation]
status: active
version: 3.0.0
updated: 2026-08-07
/L9_META -->

# Validation Checklist

## Skill pack

- [ ] `python3 scripts/validate_pack_structure.py .`
- [ ] `python3 scripts/validate_exemplary_skill.py .`
- [ ] `python3 scripts/route_plan.py --self-test`
- [ ] `python3 scripts/validate_plan_document.py fixtures/plan_pass.json` PASS
- [ ] fail fixtures FAIL with gate IDs
- [ ] `python3 scripts/self_test.py` PASS
- [ ] no omit-depth / rapid-skip language in doctrine

## Delivered plan

- [ ] PLAN_DOCUMENT emitted
- [ ] `validate_plan_document.py` PASS
- [ ] markdown projection optional only after PASS
- [ ] GMP handoff emitted when execution will follow
