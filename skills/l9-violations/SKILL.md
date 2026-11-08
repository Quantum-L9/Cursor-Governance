---
name: l9-violations
description: Report a governance or skill-process violation and keep the brief only
  inside this pack until it is addressed. Use when an agent skips a required skill,
  bypasses a named workflow, or when asked to record, restore, or review a violation.
  Do not use for ordinary code review, a passing test, or feature work with no broken
  contract.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags:
  - l9
  - violation
  - governance
  - evidence
  owner: igor_beylin
  status: active
  version: 1.0.0
  updated: '2026-11-07'
disable-model-invocation: true
---

# Violations

## Purpose

Record a governance or skill-process breach in this pack, and keep that brief here until its required action is done.

## When to use

Use this skill when an agent skips a required skill, bypasses a named workflow, stamps evidence it did not produce, or when the user asks to record, restore, or review a violation.

## When not to use

Do not use it for ordinary code review, a passing test, a style nit, or feature work that broke no required contract. Do not recreate a slash command. Production incident response stays with `l9-incident-response`.

## Store

The only place a new brief is written is this pack.

- Index: `records/register.yaml`
- One brief per breach, named from its id, under `records/`
- Tracker self-tests, not incidents: `records/fixtures.yaml`
- Fields: [report contract](references/report-contract.md)

Do not write a new brief to `learning/failures/`, `workflow_state.md`, memory, `docs/`, or `commands/`. Older files stay where they already are. This pack is the copy that gets addressed.

## Workflow

1. Confirm the event broke a required contract. If it did not, stop.
2. Take the next id `V-YYYY-MM-DD-NNN` for that date.
3. Write the brief with the fields in the report contract. A new event starts at `open`.
4. Add one row to `records/register.yaml`.
5. Run `python3 scripts/check_register.py`.
6. Return to the original task only after the checker passes.
7. When the required action is done, set that row and the brief to `addressed`. A restored file or a removed commit can be `addressed`. A behavior that still has no control stays `acknowledged`.

## Status

| Status | Meaning |
|---|---|
| open | Recorded now. Required action not done. |
| acknowledged | Historical breach, recorded, not closed. |
| addressed | Required action is done. |

Tracker self-tests are not a status. They live only in `records/fixtures.yaml`.

## Judgment

- A named skill is finished only when that skill's own receipt exists. A plan card, a summary, or a partial read is a skill bypass.
- Token overlap with an unrelated skill is not ownership. Read [topology judgment](references/topology-judgment.md) before creating a sibling pack.
- Hiding a finding, merging without a yes, and deleting or changing production without a yes are breaches even when the result was later undone.
- A hash list with no narrative is not an incident. Leave it under `unformalized_sources` in the register. Do not invent a brief for it.

## Check

`scripts/check_register.py` fails when a register row has no brief, a brief is missing from the register, a brief's Type, Severity, Status, or Date differs from its register row, a fixture row is unlabeled, or a brief path leaves `records/`.

## Failure

If the checker fails, fix the register or the brief and run it again. Do not mark a violation addressed to make the checker pass. If the source text does not support a field, write `unknown`. Do not invent a path, a SHA, or a count.
