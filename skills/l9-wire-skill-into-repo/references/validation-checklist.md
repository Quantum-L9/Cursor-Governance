# Wiring Validation Checklist (L9)

## Skill pack

- [ ] `SKILL.md` exists at `{skill-path}`
- [ ] Frontmatter `name` matches directory name
- [ ] L9 universal skills use `l9-` prefix and live under `~/.cursor/skills/`
- [ ] Frontmatter `description` has explicit triggers
- [ ] No `agents/openai.yaml`

## Repo registry (when maintaining agent docs)

- [ ] Listed in `.claude/README.md` correct table (L9 Global vs Project)
- [ ] Listed in `AGENTS.md` Skills table with matching name
- [ ] Subagent `skills:` updated only when preload required
- [ ] Trigger text consistent across registries
- [ ] No duplicate rows
- [ ] No stale paths under `.claude/skills/{structured-reasoning,skill-compiler,gmp-protocol,update-agent-docs}/`

## Fail-closed

Report `Validation: FAIL` if any mandatory item applies.
