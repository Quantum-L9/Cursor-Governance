# Skill Standard - Cursor-native frontmatter

Companion to the rules STANDARD.md. Same goal: one shape, no drift. Different
mechanism, because skills have an official escape hatch that rules do not.

## 1. The five native fields

| Field | Required | Purpose |
|---|---|---|
| `name` | Yes | Lowercase letters, numbers, hyphens. **Must match the parent folder name.** |
| `description` | Yes | What it does *and* when to use it. The entire routing signal. |
| `paths` | No | Globs. Skill surfaces only when matching files are in context. |
| `disable-model-invocation` | No | `true` = explicit `/skill-name` only, never auto-selected. |
| `metadata` | No | Arbitrary key-value mapping for additional metadata. |

## 2. Do not delete governance metadata - nest it

Unlike rules, skills accept arbitrary metadata under one key. So
`skill_schema`, `layer`, `role`, and `tags` do not get stripped. They get
moved.

Before - four unrecognized top-level keys:

```yaml
---
name: l9-gap-analysis
description: perform read-only delta gap analysis... use when assessing readiness...
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, gap-analysis, readiness, scoring, delta]
---
```

After - native shape, zero information lost:

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

## 3. Description contract

The description does the routing. Only `name` and `description` load upfront;
the body loads on invocation. So description quality is the entire cost/benefit
lever for a skill.

Required shape:

```
<what it does>. use when <trigger 1>, <trigger 2>, or <trigger 3>.
```

Optional but strongly recommended - the negative trigger:

```
... do not use when <the near-miss case that causes false activation>.
```

Your `l9-plan` already does this and it is the best description in the repo:

> create a machine-validated execution plan or implementation specification
> before building. use when scope is unclear, requirements need decomposition,
> or the next step should be planned before code changes. **do not use when the
> user only wants to execute an already-settled plan or a trivial
> fully-specified one-line fix.**

Propagate that pattern to every skill whose neighbors overlap. Priority pairs:

- `l9-code-analysis` vs `l9-inspect` vs `l9-component-verification`
- `l9-gap-analysis` vs `l9-auditing-security` vs `l9-auditing-performance`
- `l9-governance-wiring` vs `l9-governance-symlinks` vs `l9-wire-skill-into-repo`
- `l9-plan` vs `l9-ynp` vs `l9-forge`
- `l9-issue-remediation` vs `l9-pr-remediation`

Budget: 200-400 characters. Under 150 usually means the triggers are missing.
Over 500 means the body is leaking into frontmatter.

## 4. Archived skills must be locked, not just labelled

A description saying "deprecated - do not activate" is a suggestion to a
language model, not a mechanism. Deprecated skills require
`disable-model-invocation: true`, which is enforced.

Current state in this repo is inconsistent:

| archived skill | locked? |
|---|---|
| `_archived/l9-structured-reasoning-deprecated` | yes |
| `_archived/l9-pr-remediation-deprecated` | yes |
| `_archived/l9-pr-analysis` | **no - prose only** |

Two acceptable end states. Pick one and apply it uniformly:

1. Every skill under `_archived/` sets `disable-model-invocation: true`.
2. `_archived/` moves outside the skills tree entirely, e.g. `docs/archived-skills/`.

Option 2 is stronger. If discovery ever recurses, option 1 is your only defense,
and it depends on every future archival remembering the flag.

## 5. Body rules

- Filename is exactly `SKILL.md` in a folder matching `name`.
- Progressive disclosure: keep `SKILL.md` lean, push depth into sibling
  reference files the agent reads only when needed.
- Reference scripts for deterministic work rather than describing the steps in
  prose. Deterministic work belongs in a script; the skill points at it.
- State stop conditions explicitly - when the agent should pause and report a
  blocker instead of improvising.
- Name the source of truth: which files, commands, or specs are authoritative.

## 6. Budgets

| Budget | Limit |
|---|---|
| Description length | 150-500 chars |
| Non-native top-level frontmatter keys | 0 |
| `name` not matching folder name | 0 |
| Archived skills without `disable-model-invocation` | 0 |
| Total discovery footprint (names + descriptions) | 16,384 bytes |
| `SKILL.md` body | 500 lines |

Discovery footprint is the skills equivalent of the rules always-apply budget.
It is the only skill cost paid on every turn.
