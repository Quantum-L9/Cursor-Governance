<!-- L9_META
l9_schema: 1
parent: l9-plan-simple
layer: reference
role: validation_checklist
tags: [plan, validation, cursor-build]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-29
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
- [ ] Body does **not** contain a live (unnegated) `make campaign` command or a live PE execute heading
- [ ] Baseline records the current workspace; no `Lock: origin/main = <sha>`
- [ ] Body requires stacked execute: never branch from `origin/main` when any open PR exists (`PR_STACK=auto`)
- [ ] Body requires `PR_STACK=auto PR_REMEDIATE=0 make pr` after Build todos
- [ ] Body requires the finish reply to display the opened PR URL

## After Build (executor)

- [ ] Mutations landed on the unique open-PR chain tip (or `origin/main` only if the board is empty)
- [ ] `PR_STACK=auto PR_REMEDIATE=0 make pr` ran
- [ ] Opened PR URL displayed in the finish reply
