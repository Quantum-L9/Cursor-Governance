# Registry Templates (L9)

## L9 global skill — `.claude/README.md`

```markdown
| **l9-{name}** | `~/.cursor/skills/l9-{name}/` | {trigger} |
```

## Project skill — `.claude/README.md`

```markdown
| **{name}** | `skills/{name}/` | {trigger} |
```

## AGENTS.md

```markdown
| `l9-{name}` | {trigger} | — |
```

Match existing column headers in the target file.

## AUTONOMY_MANIFEST.yaml — L9 invocation tier (mandatory for L9 globals)

Auto-invoked skill (no `disable-model-invocation`) → under `tiers.auto_invoke`:

```yaml
    - skill: "l9-{name}"
      use_when: "{when triggers, mirroring the SKILL.md description}"
```

Explicit-only skill (`disable-model-invocation: true`) → under `tiers.explicit_only`:

```yaml
    - skill: "l9-{name}"
      reason: "{why it is explicit-only / high blast radius}"
```

One tier only — never both. Remove the entry when the skill is deleted.

## Subagent frontmatter

```yaml
skills:
  - l9-structured-reasoning
  - {skill-name}
```

## Global-only note

When `scope: global` and no repo registry sync requested:

```markdown
Global skill at `~/.cursor/skills/l9-{name}/`. No project copy required.
```
