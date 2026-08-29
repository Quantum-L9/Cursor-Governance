# Skills Normalization Checklist

## Stage 1 - nest (lossless)
- [ ] `docs/skills-frontmatter-archive.yaml` written before any edit
- [ ] `skill_schema` nested - count: ____
- [ ] `layer` nested - count: ____
- [ ] `role` nested - count: ____
- [ ] `tags` nested - count: ____
- [ ] Field order enforced: name, description, paths, disable-model-invocation, metadata
- [ ] No description text altered
- [ ] No `paths` added in this stage
- [ ] `name` vs folder mismatches reported - count: ____
- [ ] `AUTONOMY_MANIFEST.yaml` checked for coupling to moved fields
- [ ] Manifest accessors updated if coupled

## Stage 2 - archived lockdown
- [ ] All `_archived/` skills enumerated with their flag value
- [ ] `_archived/l9-pr-analysis` given `disable-model-invocation: true`
- [ ] Relocation of `_archived/` outside the skills tree assessed
- [ ] Decision recorded: flag-all ____ or relocate ____

## Stage 3 - measure
- [ ] `docs/skills-inventory.md` generated
- [ ] Live skill count: ____
- [ ] Discovery footprint bytes: ____ / tokens: ____
- [ ] Descriptions under 150 chars: ____
- [ ] Descriptions over 500 chars: ____
- [ ] Descriptions lacking a `use when` clause: ____
- [ ] Overlap clusters quoted side by side for human judgment
- [ ] `tools/check_skills_standard.py` wired to Makefile + pre-commit

## Stage 4 - paths (one commit each, 17 candidates)
- [ ] Each glob verified to match a non-empty file set
- [ ] Agreement checked vs `97-graph-*` rules
- [ ] Agreement checked vs `71-ci-cd-pipeline`
- [ ] Agreement checked vs `20-lang-python` / `25-python-dora-header`
- [ ] `l9-aws-secrets` scoping checked against `.cursorignore`
- [ ] Positive and negative surfacing tested per skill
- [ ] No deliberately-unscoped skill was scoped

## Sign-off

| Field | Value |
|---|---|
| Operator | |
| Date | |
| Discovery footprint before / after | |
| Non-native keys before / after | |
| Archived skills locked | |
