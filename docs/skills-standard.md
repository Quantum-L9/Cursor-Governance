# Skill Standard - Cursor-native frontmatter

Companion to [docs/rules-standard.md](rules-standard.md). Same goal: one shape,
no drift. Different mechanism, because skills have an official escape hatch
that rules do not.

Enforced by `ops/scripts/check_skills_standard.py` (`make skills-check`).

## 1. The five native fields

| Field | Required | Purpose |
|---|---|---|
| `name` | Yes | Lowercase letters, numbers, hyphens. **Must match the parent folder name.** |
| `description` | Yes | What it does *and* when to use it. The entire routing signal. |
| `paths` | No | Globs. Skill surfaces only when matching files are in context. **Incompatible with model invocation — see §paths.** |
| `disable-model-invocation` | No | `true` = explicit `/skill-name` only, never auto-selected. |
| `metadata` | No | Arbitrary key-value mapping for additional metadata. |

## 2. Do not delete governance metadata - nest it

Unlike rules, skills accept arbitrary metadata under one key. So
`skill_schema`, `layer`, `role`, `tags`, `owner`, `status`, `version`, and
`updated` do not get stripped. They get moved under `metadata:`.

```yaml
---
name: l9-gap-analysis
description: perform read-only delta gap analysis... use when assessing readiness...
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, gap-analysis, readiness, scoring, delta]
---
```

Field order is fixed: `name`, `description`, `paths`,
`disable-model-invocation`, `metadata`. Metadata last, always.

HTML `L9_META` blocks on `references/*.md` are a different contract. Do not
nest those.

## 3. Description contract

The description does the routing. Only `name` and `description` load upfront;
the body loads on invocation.

Required shape:

```
<what it does>. use when <trigger 1>, <trigger 2>, or <trigger 3>.
```

Optional but strongly recommended - the negative trigger:

```
... do not use when <the near-miss case that causes false activation>.
```

Budget: 150-500 characters. Under 150 usually means the triggers are missing.
Over 500 means the body is leaking into frontmatter.

## 4. Archived skills must be locked, not just labelled

Every skill under `skills/_archived/` must set `disable-model-invocation: true`.
A description saying "deprecated - do not activate" is not a mechanism.

Decision recorded 2026-08-13: **flag-all**. Relocate `_archived/` to
`docs/archived-skills/` is a follow-on, not this change.

## 5. Body rules

- Filename is exactly `SKILL.md` in a folder matching `name`.
- Progressive disclosure: keep `SKILL.md` lean, push depth into sibling
  reference files the agent reads only when needed.
- Reference scripts for deterministic work rather than describing the steps in
  prose.
- State stop conditions explicitly.
- Name the source of truth.

## 6. Budgets

| Budget | Limit |
|---|---|
| Description length | 150-500 chars |
| Non-native top-level frontmatter keys | 0 |
| `name` not matching folder name | 0 |
| Archived skills without `disable-model-invocation` | 0 |
| Total discovery footprint (names + descriptions) | 16,384 bytes |
| `SKILL.md` body | 500 lines (warn; pre-existing overages are not a hard fail) |

Discovery footprint is the skills equivalent of the rules always-apply budget.
It is the only skill cost paid on every turn.

A `SKILL.md` under a pack's own `tests/fixtures/` is a test fixture, not a
skill: it is never registered in `AUTONOMY_MANIFEST.yaml`, never symlinked into
an adapter, and never loaded on a turn. Those files are excluded from both the
live count and the footprint, so the budget measures what agents actually
discover.

## paths: is an availability gate, not a relevance hint

Empty `paths:` is forbidden. An empty glob hides the skill; omit the key
instead.

A **non-empty** `paths:` on a model-invocable skill is forbidden too, and the
gate rejects it. `paths:` does not merely rank a skill lower when the globs do
not match — it removes the entry from the skill listing entirely until a
matching file is in context. A skill declared `auto_invoke` in
`skills/AUTONOMY_MANIFEST.yaml` is then silently absent from every session that
has not yet touched a matching file, while the manifest and
`ops/generated/skill-registry.json` both still promise it.

Measured 2026-08-30 on the `claude-code` surface: **7/7** path-gated
model-invocable skills were missing from the session roster, and **0/16** of the
skills that did load carried the key. Perfect separation.

The key reads like a Cursor rule `globs:` — 19 `rules/*.mdc` use that key with
this same comma-separated glob syntax — where scoping is free because the rule
is consulted when relevant. For a skill the same syntax means *does not exist
yet*, and the mental model does not transfer.

Ask what actually triggers the skill. Every one of the ten gated skills answered
"a request", not "a file", in its own `description`:

- `l9-setting-up-ci` — "use when **bootstrapping** CI", gated on
  `.github/workflows/**`, the files it exists to create
- `l9-architecture-decision-records` — "use when capturing a decision", gated on
  `docs/adr/**`, the directory it exists to create
- `l9-update-agent-docs` — "use when **the user says** update agent docs", a
  phrase trigger, gated on files
- `l9-wire-skill-into-repo` — "use **immediately after** l9-skill-compiler", a
  chain trigger, gated on files

If a skill is genuinely file-triggered rather than request-triggered, gate it
with `paths:` **and** mark it `disable-model-invocation: true`, so the manifest
does not claim automatic availability the frontmatter withholds.

If the concern is context cost rather than relevance, `paths:` is the wrong
lever: it hides the skill outright. Claude Code lists **every** skill name
always and trims only descriptions under a listing budget that scales with the
context window, dropping the least-invoked first. Use
`skillOverrides: "name-only"` in settings to free budget while keeping the skill
discoverable.
