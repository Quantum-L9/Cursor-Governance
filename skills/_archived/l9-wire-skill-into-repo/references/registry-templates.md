<!-- L9_META
l9_schema: 1
parent: l9-wire-skill-into-repo
layer: reference
role: registry_templates
tags: [wiring, unwire, registry, templates, manifest]
owner: igor_beylin
status: active
version: 1.2.0
updated: 2026-08-06
/L9_META -->

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

One tier only — never both. Remove the entry when the skill is deleted **or deprecated**.

## AUTONOMY_MANIFEST.yaml — deprecated / archived (unwire)

After `git mv skills/<name> skills/_archived/<name>`:

1. Delete every tier row for `<name>`.
2. Record the archived path under `do_not_migrate_to_skills` so orphan heal never re-registers it:

```yaml
  do_not_migrate_to_skills:
    - item: "skills/_archived/l9-{name}/"
      reason: "superseded by skills/l9-{canonical}/; archived out of live skills/ discovery — never auto-invoke or reconcile"
```

Never leave a `do_not_migrate_to_skills` item pointing at a live `skills/<name>/` path once the pack has been archived.

## Subagent frontmatter

```yaml
skills:
  - l9-structured-reasoning
  - {skill-name}
```

## Global-only note

When `scope: global` and no repo registry sync requested:

```markdown
Global skill at governance `skills/l9-{name}/` (SSOT). Adapters receive symlinks; no project copy required.
```

## Historical index note (optional, after unwire)

```markdown
- [`skills/_archived/l9-{name}/`](skills/_archived/l9-{name}/) — retired; do not activate. Use `l9-{canonical}`.
```

Live skill tables must not list archived packs as available skills.
