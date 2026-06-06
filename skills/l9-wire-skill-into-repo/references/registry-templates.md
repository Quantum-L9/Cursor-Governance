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
