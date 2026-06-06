---
name: l9-wire-skill-into-repo
description: Registers new or updated agent skills into repo discovery tables, subagent preload lists, and related agent docs after skill creation. Use immediately after l9-skill-compiler finishes, when the user asks to wire or register a skill, or when a skill pack exists but is not yet discoverable.
---

# Wire Skill Into Repo (L9)

## Purpose

A skill is **not complete** until agents can discover it. Run as the **final step** after `l9-skill-compiler` delivers a skill pack.

## Inputs (gather first)

| Field | Required | Notes |
|-------|----------|-------|
| `skill-name` | yes | Must match directory name and frontmatter `name` |
| `skill-path` | yes | Absolute or repo-relative path to skill folder |
| `description` | yes | Lowercase what + when (same text used in all registries) |
| `scope` | yes | `global` or `project` |
| `preload-subagents` | no | Which subagents should preload via `skills:` frontmatter |

If any required field is missing, stop and ask — do not guess registry rows.

## Scope rules

| Scope | Skill location | Repo wiring |
|-------|----------------|-------------|
| **global** | `~/.cursor/skills/l9-{name}/` or `~/.cursor/skills/{name}/` | Register in repo **L9 Global Skills** table when maintaining agent docs in a project repo |
| **project** | `.cursor/skills/` or `.claude/skills/` | **Mandatory** — Project Skills table + AGENTS.md |

L9 universal skills use the `l9-` prefix and live only under `~/.cursor/skills/`. Do not duplicate L9 packs into `.claude/skills/`.

## Workflow

```
Task Progress:
- [ ] Step 1: Confirm skill pack + metadata
- [ ] Step 2: Detect repo registry layout
- [ ] Step 3: Apply project-specific adapter (if present)
- [ ] Step 4: Update registries
- [ ] Step 5: Validate wiring
- [ ] Step 6: Report what changed
```

### Step 1: Confirm skill pack

- [ ] `{skill-path}/SKILL.md` exists and is non-empty
- [ ] Frontmatter `name` matches directory name
- [ ] Frontmatter `description` includes explicit trigger terms
- [ ] No `agents/openai.yaml`

### Step 2: Detect registry layout

| Signal | Registry target |
|--------|-----------------|
| `.claude/README.md` L9 Global Skills / Project Skills tables | Skill index |
| `AGENTS.md` Agent Skills table | Cross-tool index |
| `.claude/agents/*.md` `skills:` frontmatter | Subagent preload |
| `CLAUDE.md` Imports/References | Foundational skills only |

Load [references/layout-detection.md](references/layout-detection.md) when ambiguous.

### Step 3: Project-specific adapter

Probe in order:

1. `.claude/adapters/plasticos-repo-wiring.md`
2. `.claude/adapters/{name}-repo-wiring.md`
3. Repo-local `.cursor/skills/l9-wire-skill-into-repo/references/project-adapter.md`

Adapter wins over generic templates.

### Step 4: Update registries

Use identical trigger text everywhere.

**L9 global skill** (`.claude/README.md` → L9 Global Skills):

```markdown
| **l9-{name}** | `~/.cursor/skills/l9-{name}/` | {trigger} |
```

**Project skill** (`.claude/README.md` → Project Skills):

```markdown
| **{name}** | `skills/{name}/` | {trigger} |
```

**`AGENTS.md`** — match existing column format; include global path for L9 skills.

**Subagents** — update `skills:` only when preload required (see adapter).

Templates: [references/registry-templates.md](references/registry-templates.md)

### Step 5: Validate

[references/validation-checklist.md](references/validation-checklist.md). Fail closed if mandatory registry missing.

### Step 6: Report

```markdown
## Wiring complete: {skill-name}

- Scope: {global|project}
- Pack: {skill-path}
- Updated: {files or "registry sync only"}
- Subagents preloaded: {list or "none"}
- Validation: PASS | FAIL ({blocker})
```

## Daisy-chain contract

| Upstream | When |
|----------|------|
| `l9-skill-compiler` | After build, before validation sign-off |

## Additional resources

- [references/layout-detection.md](references/layout-detection.md)
- [references/registry-templates.md](references/registry-templates.md)
- [references/validation-checklist.md](references/validation-checklist.md)
