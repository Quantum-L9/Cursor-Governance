<!-- L9_META
l9_schema: 1
parent: l9-wire-skill-into-repo
layer: reference
role: validation_checklist
tags: [wiring, unwire, validation, checklist, registry]
owner: igor_beylin
status: active
version: 1.2.0
updated: 2026-08-06
/L9_META -->

# Wiring Validation Checklist (L9)

## Skill pack (wire)

- [ ] `SKILL.md` exists at `{skill-path}`
- [ ] Frontmatter `name` matches directory name
- [ ] L9 universal skills use `l9-` prefix and live under governance `skills/` SSOT
- [ ] Frontmatter `description` has explicit triggers
- [ ] `agents/meta.yaml` present when packaging for adapter display; no `agents/openai.yaml`
- [ ] Skill discoverable under `.claude/skills/{name}/` via adapter symlink (not a sibling under `.claude/`)
- [ ] Frontmatter `status` is not `deprecated` at a live discovery path

## Repo registry (wire — when maintaining agent docs)

- [ ] Listed in `.claude/README.md` correct table (L9 Global vs Project)
- [ ] Listed in `AGENTS.md` Skills table with matching name
- [ ] **L9 global skill present in `AUTONOMY_MANIFEST.yaml` — exactly one tier (`auto_invoke` if auto-invoked, else `explicit_only`); never both**
- [ ] Subagent `skills:` updated only when preload required
- [ ] Trigger text consistent across registries
- [ ] No duplicate rows
- [ ] No stale paths under `.claude/skills/{structured-reasoning,skill-compiler,gmp-protocol,update-agent-docs}/`

## Unwire / deprecate (mandatory when retiring)

- [ ] Pack moved with `git mv` to `skills/_archived/{name}/` (or project archive equivalent)
- [ ] **No** remaining top-level `skills/{name}/`
- [ ] Frontmatter has `status: deprecated` and `disable-model-invocation: true`
- [ ] `superseded_by` set when a canonical replacement exists
- [ ] Removed from `AUTONOMY_MANIFEST.yaml` `tiers.auto_invoke` and `tiers.explicit_only`
- [ ] `do_not_migrate_to_skills` entry points at `skills/_archived/{name}/`
- [ ] Absent from generated skill-registry
- [ ] Adapter symlinks removed (`~/.claude/skills/{name}`, `<workspace>/.claude/skills/{name}`)
- [ ] Removed from docs skill tables as an activatable skill
- [ ] Removed from subagent `skills:` preload lists
- [ ] `sync_generated_artifacts` / live-deprecated guard would PASS
- [ ] Report uses unwire template from [unwire-deprecate.md](unwire-deprecate.md)

## Fail-closed

Report `Validation: FAIL` if any mandatory item applies.

- Wire: trigger text MUST be identical across registries.
- Unwire: `status: deprecated` while still under live `skills/` is always FAIL.
