---
name: l9-create-skill
description: Creates Cursor Agent Skills with L9 naming for universal packs and chains repo registration via l9-wire-skill-into-repo. Use when authoring a new skill, asking about SKILL.md structure, or after /create-skill.
---

# Creating Skills (L9)

Global skill at `~/.cursor/skills/l9-create-skill/`. Chains **`l9-wire-skill-into-repo`** as mandatory Phase 5.

For multi-file zero-stub packs, use **`l9-skill-compiler`** instead.

## Naming

| Type | Directory | Example |
|------|-----------|---------|
| **L9 universal** | `~/.cursor/skills/l9-{name}/` | `l9-structured-reasoning` |
| **Project domain** | `.claude/skills/plasticos-{name}/` or `.claude/skills/{name}/` | `plasticos-pr-review-kernel` |

Never create skills in `~/.cursor/skills-cursor/`.

## Before You Begin

Gather purpose, scope, triggers, domain knowledge, output format, and existing patterns. Use user wording **verbatim** when supplied.

## SKILL.md Template

```yaml
---
name: l9-your-skill-name
description: third-person what + when triggers (lowercase)
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, ...]
owner: igor_beylin
status: active
version: 1.0.0
updated: YYYY-MM-DD
---
```

Project-only skills may omit audit fields; L9 universal skills should include them.

## Workflow

1. **Discovery** — purpose, scope, triggers
2. **Design** — name, file tree, references
3. **Implementation** — complete files only (no stubs)
4. **Verification** — name matches dir, triggers in description, <500 lines, no `agents/openai.yaml`
5. **Wire** — load **`l9-wire-skill-into-repo`** (`~/.cursor/skills/l9-wire-skill-into-repo/SKILL.md`); pass `skill-name`, `skill-path`, `description`, `scope`

**Not complete until Phase 5 reports `Validation: PASS`.**

## Related L9 skills

| Skill | Path |
|-------|------|
| **l9-wire-skill-into-repo** | `~/.cursor/skills/l9-wire-skill-into-repo/` |
| **l9-skill-compiler** | `~/.cursor/skills/l9-skill-compiler/` |
