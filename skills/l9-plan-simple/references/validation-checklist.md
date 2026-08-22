<!-- L9_META
l9_schema: 1
parent: l9-plan-simple
layer: reference
role: validation_checklist
tags: [plan, validation, cursor-build]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-21
/L9_META -->

# Validation Checklist

## Skill pack

- [ ] `SKILL.md` + `agents/meta.yaml` present; no `agents/openai.yaml`
- [ ] `references/executable-plan.template.md` is a symlink to the first-class SSOT
- [ ] No forked copy of `canonical.template.executable_plan.v1.plan.md`
- [ ] Reuses `l9-plan` schema + `validate_plan_document.py` (not copied)

## Delivered plan

- [ ] PLAN_DOCUMENT emitted
- [ ] `python3 ../l9-plan/scripts/validate_plan_document.py <plan.json>` PASS
- [ ] `.plan.md` projected with `--execute-via=cursor-build` (or hand-filled with the execute swap)
- [ ] Frontmatter has `kind: simple` and `execute_via: cursor-build`
- [ ] Body has **Execute via Cursor Build**
- [ ] Body does **not** contain `make campaign` or a live PE execute heading
- [ ] Baseline records the current workspace; no `Lock: origin/main = <sha>`
