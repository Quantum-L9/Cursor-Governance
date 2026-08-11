<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: validation_checklist
tags: [issues, validation, done-when]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-11
/L9_META -->

# Validation Checklist

## Pack structure

- [ ] `SKILL.md` frontmatter: name, description, audit fields, `disable-model-invocation: true`
- [ ] `agents/meta.yaml` present; no `agents/openai.yaml`
- [ ] Every `references/` file linked from `SKILL.md`
- [ ] Every `scripts/` file named in SKILL.md or linked refs
- [ ] Zero stub / TBD / unfinished sections

## Diagnose

- [ ] `fleet_discover.py` returns non-archived Quantum-L9 repos
- [ ] `issue_ingest.py` produces secret-free JSON
- [ ] Verdict emitted only after ingest
- [ ] No mutations

## Converge

- [ ] Sticky cluster ≤ 1 per default invoke
- [ ] Ownership classified before edit
- [ ] CROSS_REPO fixed at obvious owner
- [ ] Cycles ≤ 3; one commit/push per cycle
- [ ] No workflow/CI infra edits; no merge; no force-push
- [ ] PR work handed to `l9-pr-remediation`
- [ ] PICKUP required; issue comments on all cluster issues
- [ ] `TODO.md` updated only when pre-existing

## Wiring

- [ ] `l9-wire-skill-into-repo` PASS
- [ ] `AUTONOMY_MANIFEST.yaml` `explicit_only` row present
- [ ] `/issues` command delegates Diagnose only
