<!-- L9_META
l9_schema: 1
parent: l9-plan-simple
layer: reference
role: validation_checklist
tags: [plan, validation, cursor-build, embedded]
owner: igor_beylin
status: active
version: 1.2.0
updated: 2026-09-02
/L9_META -->

# Validation Checklist

## Skill pack

- [ ] `SKILL.md` + `agents/meta.yaml` present; no `agents/openai.yaml`
- [ ] `references/executable-plan.template.md` is a symlink to the first-class SSOT
- [ ] No forked copy of `canonical.template.executable_plan.v1.plan.md`
- [ ] Reuses `l9-plan` schema + `validate_plan_document.py` (not copied)
- [ ] One renderer for every mode — no per-mode copy of `render_plan_pe_autonomy.py`

## Delivered plan — both modes

- [ ] PLAN_DOCUMENT emitted
- [ ] `python3 ../l9-plan/scripts/validate_plan_document.py <plan.json>` PASS
- [ ] Handoff mode was selected explicitly, not inferred from missing capabilities
- [ ] `.plan.md` projected with the mode's `--execute-via` (or hand-filled with that mode's execute swap)
- [ ] Frontmatter has `kind: simple` and the selected `execute_via`
- [ ] Stress-test and leverage pass present (no mode skips it)
- [ ] Baseline records the current workspace; no `Lock: origin/main = <sha>`
- [ ] Body does **not** contain a live (unnegated) `make campaign` command or a live PE execute heading

## Delivered plan — `cursor-build` (default)

- [ ] Frontmatter `execute_via: cursor-build`
- [ ] Body has **Execute via Cursor Build**
- [ ] Body requires stacked execute: never branch from `origin/main` when any open PR exists (`PR_STACK=auto`)
- [ ] Body requires `PR_STACK=auto PR_REMEDIATE=0 make pr` after Build todos
- [ ] Body requires the finish reply to display the opened PR URL

## Delivered plan — `embedded`

- [ ] Frontmatter `execute_via: embedded`
- [ ] Body has **Handoff to Caller**
- [ ] Body states the caller owns all downstream execution and must enforce its own authority
- [ ] Body contains no live `Press **Build**`, `PR_STACK=auto`, `PR_REMEDIATE=0`, `make pr`, PR-URL, `agent_worktree_start.sh`, or `make campaign` instruction
- [ ] Body admits no Program Lock, Controller lease, phased execution protocol, or deployment authority
- [ ] Reply records the caller handoff and stops — no branch, commit, publication, or PR performed or requested

## After Build (`cursor-build` executor only)

- [ ] Mutations landed on the unique open-PR chain tip (or `origin/main` only if the board is empty)
- [ ] `PR_STACK=auto PR_REMEDIATE=0 make pr` ran
- [ ] Opened PR URL displayed in the finish reply

`embedded` has no executor phase. Nothing runs after the handoff; the caller's own contract governs whatever it does next.
